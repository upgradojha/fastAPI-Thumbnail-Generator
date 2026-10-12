"""Bounded in-process job queue; jobs and individual thumbnails persist in SQLite.

Suitable for running ONE Uvicorn worker. In production use Celery/Redis or another
external queue rather than multiple ASGI processes (see README).
"""
import asyncio
import base64
import logging
from sqlalchemy import select
from .config import settings
from .database import Job, Thumbnail, SessionLocal
from .media import local_ref_path, make_demo, store_thumbnail
from .styles import STYLES

log = logging.getLogger(__name__)


class JobManager:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=settings.queue_size)
        self.workers = []

    async def start(self):
        # Restart any interrupted jobs from persisted state.
        with SessionLocal() as db:
            interrupted = db.scalars(select(Job).where(Job.status.in_(['pending', 'processing']))).all()
            for job in interrupted:
                job.status = 'pending'
                for thumb in job.thumbnails:
                    if thumb.status not in ('done', 'failed'):
                        thumb.status = 'pending'
            db.commit()
            ids = [job.id for job in interrupted]
        # Start workers before replaying queue. Queue stays bounded at runtime.
        self.workers = [asyncio.create_task(self.worker(i), name=f'thumb-worker-{i}') for i in range(settings.worker_count)]
        for job_id in ids:
            await self.queue.put(job_id)

    async def stop(self):
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    async def worker(self, index: int):
        while True:
            job_id = await self.queue.get()
            try:
                await self.process(job_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception('Unexpected job failure: %s', job_id)
                with SessionLocal() as db:
                    job = db.get(Job, job_id)
                    if job:
                        job.status = 'failed'
                        db.commit()
            finally:
                self.queue.task_done()

    async def process(self, job_id: str):
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if not job:
                return
            job.status = 'processing'
            db.commit()
            prompt = job.prompt
            ref_id = job.reference_id
            pending_ids = [t.id for t in job.thumbnails if t.status != 'done']
        # Each thumbnail fails independently, and individual output is persisted.
        await asyncio.gather(*(self.generate(thumb_id, job_id, ref_id, prompt) for thumb_id in pending_ids))
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if not job:
                return
            job.status = 'completed' if any(t.status == 'done' for t in job.thumbnails) else 'failed'
            db.commit()

    async def generate(self, thumb_id: str, job_id: str, ref_id: str, prompt: str):
        try:
            with SessionLocal() as db:
                thumb = db.get(Thumbnail, thumb_id)
                if not thumb:
                    return
                thumb.status = 'processing'
                style = thumb.style_name
                db.commit()
            reference = local_ref_path(ref_id).read_bytes()
            if settings.generator == 'demo':
                generated = await asyncio.to_thread(make_demo, reference, prompt, style)
            else:
                generated = await self.generate_ai(reference, prompt, style)
            url = await store_thumbnail(thumb_id, job_id, generated)
            with SessionLocal() as db:
                thumb = db.get(Thumbnail, thumb_id)
                if thumb:
                    thumb.image_url = url
                    thumb.status = 'done'
                    thumb.error_message = None
                    db.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception('Generation failed: %s', thumb_id)
            with SessionLocal() as db:
                thumb = db.get(Thumbnail, thumb_id)
                if thumb:
                    thumb.status = 'failed'
                    thumb.error_message = f'{type(exc).__name__}: {exc}'[:400]
                    db.commit()

    @staticmethod
    async def generate_ai(reference: bytes, prompt: str, style_name: str) -> bytes:
        instruction = STYLES[style_name]['instruction']
        full_prompt = (
            'Create one beautiful, professional YouTube video thumbnail. Use the attached '
            'reference photo as the likeness/portrait reference when relevant, preserving identity. '
            'Produce a polished horizontal 16:9-style editorial composition, impactful at small sizes. '
            'Topic and exact requested emphasis: ' + prompt + '. '
            'Creative art direction: ' + instruction + ' '
            'If text is present, keep it short and legible. No watermarks, no confusing interface chrome.'
        )
        from openai import AsyncOpenAI  # optional in offline demo mode
        async with AsyncOpenAI(api_key=settings.openai_key, timeout=180.0) as client:
            result = await client.images.edit(
                model=settings.image_model,
                image=('reference.jpg', reference, 'image/jpeg'),
                prompt=full_prompt,
                size='1536x1024',
                quality=settings.image_quality,
                output_format='png',
                n=1,
            )
        if not result.data or not result.data[0].b64_json:
            raise RuntimeError('OpenAI returned no image data')
        return base64.b64decode(result.data[0].b64_json)


manager = JobManager()
