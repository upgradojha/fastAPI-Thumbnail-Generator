"""Image validation, local files, demo graphics, and ImageKit remote storage."""
import io
import textwrap
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from uuid import uuid4
import httpx
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError
from fastapi import HTTPException
from .config import MEDIA, settings

MEDIA.mkdir(parents=True, exist_ok=True)
VARIANTS = {'youtube': (1280, 720), 'shorts': (1080, 1920), 'square': (1080, 1080)}


def validate_image(data: bytes) -> bytes:
    if not data or len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f'Image must be between 1 byte and {settings.max_upload_mb} MB')
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.width * im.height > 25_000_000:
                raise ValueError('Image resolution exceeds 25 megapixels')
            if im.format not in {'JPEG', 'PNG', 'WEBP'}:
                raise ValueError('Only JPEG, PNG, and WebP are supported')
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            im = ImageOps.exif_transpose(im)
            im.thumbnail((2400, 2400))
            im = im.convert('RGB')
            out = io.BytesIO()
            im.save(out, format='JPEG', quality=91, optimize=True)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(400, f'Invalid image: {exc}') from exc


def local_ref_path(ref_id: str) -> Path:
    return MEDIA / 'references' / f'{ref_id}.jpg'


def local_thumb_path(thumb_id: str) -> Path:
    return MEDIA / 'thumbnails' / f'{thumb_id}.png'


def write_file(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


async def upload_imagekit(data: bytes, file_name: str, folder: str) -> str:
    async with httpx.AsyncClient(timeout=100.0) as client:
        resp = await client.post('https://upload.imagekit.io/api/v1/files/upload',
            auth=(settings.imagekit_key, ''),
            data={'fileName': file_name, 'folder': folder, 'useUniqueFileName': 'true', 'isPrivateFile': 'false'},
            files={'file': (file_name, data, 'image/png' if file_name.endswith('.png') else 'image/jpeg')})
        resp.raise_for_status()
        body = resp.json()
        if not body.get('url'):
            raise RuntimeError('ImageKit upload response did not contain a URL')
        return body['url']


async def store_reference(data: bytes) -> tuple[str, str]:
    ref_id = str(uuid4())
    # Always retain the uploaded input locally for image editing (never fetch user-supplied URLs).
    write_file(local_ref_path(ref_id), data)
    if settings.storage == 'imagekit':
        try:
            url = await upload_imagekit(data, f'{ref_id}.jpg', '/thumbnail-studio/references')
        except Exception:
            local_ref_path(ref_id).unlink(missing_ok=True)
            raise
    else:
        url = f'/api/references/{ref_id}'
    return ref_id, url


async def store_thumbnail(thumb_id: str, job_id: str, data: bytes) -> str:
    if settings.storage == 'imagekit':
        return await upload_imagekit(data, f'{thumb_id}.png', f'/thumbnail-studio/{job_id}')
    write_file(local_thumb_path(thumb_id), data)
    return f'/api/thumbnails/{thumb_id}/image/original'


def get_variants(thumb_id: str, image_url: str | None) -> dict:
    if not image_url:
        return {}
    if settings.storage == 'local' or image_url.startswith('/api/'):
        return {k: f'/api/thumbnails/{thumb_id}/image/{k}' for k in VARIANTS}
    split = urlsplit(image_url)
    result = {}
    for key, (width, height) in VARIANTS.items():
        query = [(k, v) for k, v in parse_qsl(split.query, keep_blank_values=True) if k != 'tr']
        query.append(('tr', f'w-{width},h-{height},fo-auto'))
        result[key] = urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))
    return result


def resize_variant(image_data: bytes, variant: str) -> bytes:
    if variant == 'original':
        return image_data
    dims = VARIANTS.get(variant)
    if dims is None:
        raise KeyError(variant)
    with Image.open(io.BytesIO(image_data)) as im:
        im = ImageOps.fit(im.convert('RGB'), dims, method=Image.Resampling.LANCZOS, centering=(0.5, 0.43))
        b = io.BytesIO()
        im.save(b, format='JPEG', quality=89, optimize=True)
        return b.getvalue()


def font(size: int, bold=True):
    paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
    ] if bold else ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf']
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_demo(reference: bytes, prompt: str, style_name: str) -> bytes:
    """OFFLINE demo: poster template drawn locally. Does NOT claim to be AI-generated."""
    colors = {'bold': ('#191a24', '#f7bb54', '#fff5dd'), 'minimal': ('#192e33', '#b9edcf', '#ecfff5'), 'vibrant': ('#392d5a', '#f978c8', '#fff3fa')}
    bg, accent, fg = colors[style_name]
    im = Image.new('RGB', (1536, 864), bg)
    draw = ImageDraw.Draw(im)
    # Geometric accents, left side for clear headline + clean right-side portrait.
    draw.ellipse((1000,-280,1860,570), fill=accent)
    draw.rounded_rectangle((50,60,870,804), radius=48, fill='#11161d')
    draw.rounded_rectangle((94,104,244,145), radius=20, fill=accent)
    draw.text((119,111), 'STUDIO', font=font(19), fill='#141620')
    words = [s.upper() for s in prompt.replace('—',' ').split() if s]
    title = ' '.join(words[:7]) or 'YOUR BIG IDEA'
    lines = textwrap.wrap(title, width=13, break_long_words=True)[:4]
    y = 245
    title_font = font(88)
    for line in lines:
        draw.text((96,y), line, fill=fg, font=title_font, stroke_width=1)
        y += 107
    draw.rectangle((96,690,520,702), fill=accent)
    draw.text((96,732), 'CREATOR SERIES   /   01', font=font(25), fill=accent)
    with Image.open(io.BytesIO(reference)) as ref:
        ref = ImageOps.fit(ref.convert('RGB'), (520,590), centering=(0.5,0.4))
        mask = Image.new('L', (520,590), 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle((0,0,519,589), radius=45, fill=255)
        im.paste(ref, (927,174), mask)
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((924,171,1450,770), radius=45, outline=accent, width=9)
    out = io.BytesIO()
    im.save(out, format='PNG', optimize=True)
    return out.getvalue()
