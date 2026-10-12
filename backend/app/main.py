"""HTTP API, uploaded image ingestion, status endpoints and server-sent events."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from .config import MEDIA, settings
from .database import Job, Thumbnail, SessionLocal, create_tables
from .media import VARIANTS, get_variants, local_ref_path, local_thumb_path, resize_variant, store_reference, validate_image
from .styles import STYLES
from .worker import manager

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    (MEDIA.parent).mkdir(parents=True, exist_ok=True)
    create_tables()
    await manager.start()
    try:
        yield
    finally:
        await manager.stop()


app = FastAPI(title='Thumbnail Studio API', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()], allow_methods=['GET','POST'], allow_headers=['*'])


class CreateJob(BaseModel):
    prompt: str = Field(min_length=5, max_length=1500)
    reference_id: str
    styles: list[str] = Field(min_length=1, max_length=3)

    @field_validator('prompt')
    @classmethod
    def clean_prompt(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError('Write at least 5 characters')
        return value

    @field_validator('reference_id')
    @classmethod
    def valid_uuid(cls, value):
        try:
            return str(UUID(value))
        except ValueError as exc:
            raise ValueError('Invalid reference ID') from exc

    @field_validator('styles')
    @classmethod
    def valid_styles(cls, value):
        if len(set(value)) != len(value) or not all(v in STYLES for v in value):
            raise ValueError('Choose 1–3 distinct supported styles')
        return value


def render_thumb(thumb: Thumbnail) -> dict:
    return dict(id=thumb.id, style=thumb.style_name, style_label=STYLES[thumb.style_name]['name'],
        status=thumb.status, image_url=thumb.image_url,
        variants=get_variants(thumb.id, thumb.image_url), error_message=thumb.error_message)


def render_job(job: Job) -> dict:
    return dict(id=job.id, prompt=job.prompt, status=job.status,
        created_at=job.created_at.isoformat(), reference_url=job.headshot_url,
        thumbnails=[render_thumb(t) for t in sorted(job.thumbnails, key=lambda t: t.created_at)])


@app.get('/api/health')
def health():
    return {'status': 'ok', 'generator': settings.generator, 'storage': settings.storage}


@app.get('/api/styles')
def styles():
    return [{'id': k, **v} for k, v in STYLES.items()]


@app.post('/api/upload-headshot')
async def upload_headshot(image: UploadFile = File(...)):
    # Small bounded read prevents arbitrarily large uploads from exhausting RAM.
    data = await image.read(settings.max_upload_mb * 1024 * 1024 + 1)
    clean = validate_image(data)
    try:
        ref_id, url = await store_reference(clean)
    except Exception as exc:
        logging.exception('Reference upload failed')
        raise HTTPException(502, f'Image storage failed: {type(exc).__name__}') from exc
    return {'reference_id': ref_id, 'url': url}


@app.get('/api/references/{reference_id}')
def reference_image(reference_id: UUID):
    path = local_ref_path(str(reference_id))
    if not path.is_file():
        raise HTTPException(404, 'Reference not found')
    return FileResponse(path, media_type='image/jpeg')


@app.post('/api/jobs', status_code=202)
async def create_job(data: CreateJob):
    if not local_ref_path(data.reference_id).is_file():
        raise HTTPException(404, 'Reference image not found; upload it first')
    if manager.queue.full():
        raise HTTPException(429, 'Generation queue is full; retry later')
    with SessionLocal() as db:
        # HEADSHOT comes from our upload record, never a client-supplied external URL.
        ref_url = f'/api/references/{data.reference_id}'
        job = Job(prompt=data.prompt, reference_id=data.reference_id, headshot_url=ref_url)
        job.thumbnails = [Thumbnail(style_name=style) for style in data.styles]
        db.add(job)
        db.commit()
        job_id = job.id
    manager.queue.put_nowait(job_id)
    return {'job_id': job_id}


@app.get('/api/jobs')
def list_jobs():
    with SessionLocal() as db:
        jobs = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(40)).all()
        return [render_job(j) for j in jobs]


@app.get('/api/jobs/{job_id}')
def get_job(job_id: UUID):
    with SessionLocal() as db:
        job = db.get(Job, str(job_id))
        if not job:
            raise HTTPException(404, 'Job not found')
        return render_job(job)


@app.get('/api/thumbnails/{thumb_id}/image/{variant}')
def thumbnail_image(thumb_id: UUID, variant: str):
    if variant not in (*VARIANTS, 'original'):
        raise HTTPException(404, 'Unknown size')
    with SessionLocal() as db:
        thumb = db.get(Thumbnail, str(thumb_id))
        if not thumb or thumb.status != 'done':
            raise HTTPException(404, 'Thumbnail is not ready')
    path = local_thumb_path(str(thumb_id))
    if not path.is_file():
        raise HTTPException(404, 'Local thumbnail not found (may be in ImageKit)')
    if variant == 'original':
        return FileResponse(path, media_type='image/png')
    result = resize_variant(path.read_bytes(), variant)
    return Response(content=result, media_type='image/jpeg', headers={'Cache-Control':'public, max-age=3600'})


@app.get('/api/jobs/{job_id}/events')
async def stream_job(job_id: UUID):
    with SessionLocal() as db:
        if not db.get(Job, str(job_id)):
            raise HTTPException(404, 'Job not found')

    async def stream():
        previous = None
        last_heartbeat = asyncio.get_running_loop().time()
        yield 'retry: 3000\n\n'
        while True:
            with SessionLocal() as db:
                job = db.get(Job, str(job_id))
                snapshot = render_job(job) if job else None
            if not snapshot:
                yield 'event: error\ndata: {"message":"Job deleted"}\n\n'
                break
            payload = json.dumps(snapshot)
            if payload != previous:
                yield f'event: job_update\ndata: {payload}\n\n'
                previous = payload
            if snapshot['status'] in {'completed', 'failed'}:
                yield f'event: job_completed\ndata: {payload}\n\n'
                break
            now = asyncio.get_running_loop().time()
            if now - last_heartbeat >= 15:
                yield ': keepalive\n\n'
                last_heartbeat = now
            # The HTTP connection stays open; the browser does not poll.
            await asyncio.sleep(0.85)

    return StreamingResponse(stream(), media_type='text/event-stream', headers={
        'Cache-Control':'no-cache, no-transform', 'X-Accel-Buffering':'no', 'Connection':'keep-alive'
    })
