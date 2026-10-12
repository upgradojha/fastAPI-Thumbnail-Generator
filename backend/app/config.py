"""Configuration, loaded from backend/.env (not committed to git)."""
from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def positive_int(name: str, default: int) -> int:
    try:
        result = int(os.getenv(name, str(default)))
        if result < 1:
            raise ValueError()
        return result
    except ValueError as exc:
        raise RuntimeError(f'{name} must be a positive integer') from exc


@dataclass(frozen=True)
class Settings:
    generator: str = os.getenv('GENERATOR_BACKEND', 'demo').lower()
    storage: str = os.getenv('STORAGE_BACKEND', 'local').lower()
    openai_key: str = os.getenv('OPENAI_API_KEY', '')
    image_model: str = os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-2')
    image_quality: str = os.getenv('OPENAI_IMAGE_QUALITY', 'high')
    imagekit_key: str = os.getenv('IMAGEKIT_PRIVATE_KEY', '')
    imagekit_endpoint: str = os.getenv('IMAGEKIT_URL_ENDPOINT', '').rstrip('/')
    cors_origins: str = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
    max_upload_mb: int = positive_int('MAX_UPLOAD_MB', 8)
    worker_count: int = positive_int('WORKER_COUNT', 2)
    queue_size: int = positive_int('QUEUE_SIZE', 30)
    database_url: str = os.getenv('DATABASE_URL') or f'sqlite:///{(ROOT / "data" / "studio.db").as_posix()}'

    def validate(self):
        if self.generator not in ('demo', 'openai'):
            raise RuntimeError('GENERATOR_BACKEND must be demo or openai')
        if self.storage not in ('local', 'imagekit'):
            raise RuntimeError('STORAGE_BACKEND must be local or imagekit')
        if self.generator == 'openai' and not self.openai_key:
            raise RuntimeError('OPENAI_API_KEY is needed for GENERATOR_BACKEND=openai')
        if self.storage == 'imagekit' and (not self.imagekit_key or not self.imagekit_endpoint):
            raise RuntimeError('IMAGEKIT_PRIVATE_KEY and IMAGEKIT_URL_ENDPOINT are required for STORAGE_BACKEND=imagekit')


settings = Settings()
MEDIA = ROOT / 'data' / 'media'
