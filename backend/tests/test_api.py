"""Offline integration tests; paid services aren't contacted."""
import io
import os
import tempfile
import time
from pathlib import Path
from PIL import Image

# Set all environment overrides BEFORE importing the application.
_test_dir = tempfile.mkdtemp(prefix='studio-tests-')
os.environ['DATABASE_URL'] = f'sqlite:///{_test_dir}/test.db'
os.environ['GENERATOR_BACKEND'] = 'demo'
os.environ['STORAGE_BACKEND'] = 'local'

from fastapi.testclient import TestClient
from app.main import app


def small_image():
    out = io.BytesIO()
    Image.new('RGB', (180, 180), '#9579c4').save(out, 'JPEG')
    return out.getvalue()


def test_end_to_end():
    with TestClient(app) as client:
        health = client.get('/api/health')
        assert health.status_code == 200
        assert health.json()['generator'] == 'demo'
        assert len(client.get('/api/styles').json()) == 3
        upload = client.post('/api/upload-headshot', files={'image':('face.jpg',small_image(),'image/jpeg')})
        assert upload.status_code == 200, upload.text
        ref = upload.json()['reference_id']
        bad_job = client.post('/api/jobs',json={'reference_id':ref,'prompt':'short','styles':['bold','bold']})
        assert bad_job.status_code == 422
        created = client.post('/api/jobs',json={'reference_id':ref,'prompt':'Learn Python FastAPI in 30 minutes','styles':['bold','minimal']})
        assert created.status_code == 202, created.text
        jobid = created.json()['job_id']
        deadline = time.time()+35
        while time.time() < deadline:
            result = client.get(f'/api/jobs/{jobid}').json()
            if result['status'] in ('completed','failed'):
                break
            time.sleep(.15)
        assert result['status'] == 'completed', result
        assert len(result['thumbnails']) == 2
        assert all(t['status']=='done' for t in result['thumbnails']), result
        for t in result['thumbnails']:
            for kind, dims in [('youtube',(1280,720)),('shorts',(1080,1920)),('square',(1080,1080))]:
                image = client.get(t['variants'][kind])
                assert image.status_code == 200
                assert Image.open(io.BytesIO(image.content)).size == dims
        with client.stream('GET', f'/api/jobs/{jobid}/events') as response:
            data = ''.join(response.iter_text())
            assert 'event: job_update' in data
            assert 'event: job_completed' in data
        assert any(j['id'] == jobid for j in client.get('/api/jobs').json())


def test_bad_image_and_not_found():
    with TestClient(app) as client:
        bad = client.post('/api/upload-headshot',files={'image':('fake.png',b'not an image','image/png')})
        assert bad.status_code == 400
        missing = client.get('/api/jobs/11111111-1111-4111-8111-111111111111')
        assert missing.status_code == 404


def test_imagekit_variants_url():
    from app.media import get_variants
    from app.config import settings
    from unittest.mock import patch
    from dataclasses import replace
    # Remote URLs use ImageKit's single-original, three-resize URL transformation.
    with patch('app.media.settings', replace(settings, storage='imagekit')):
        variants = get_variants('example', 'https://ik.imagekit.io/demo/folder/demo.png')
        assert variants['youtube'].endswith('?tr=w-1280%2Ch-720%2Cfo-auto')
        assert variants['shorts'].endswith('?tr=w-1080%2Ch-1920%2Cfo-auto')
