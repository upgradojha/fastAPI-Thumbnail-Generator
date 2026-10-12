# Framecraft — AI Thumbnail Studio

A full-stack thumbnail builder inspired by the attached FastAPI + React tutorial. Upload a reference photo, write a description, pick 1–3 styles, watch real-time job progress (SSE), and export YouTube, Shorts, and square versions. Jobs are saved in SQLite.

## Get started (2 minutes)

**Requirements:** Python 3.11+ and Node.js 20+ (includes npm). Internet needed the first time to install packages.

1. Extract this ZIP.
2. **Windows:** double-click `start_windows.bat`. **macOS/Linux:** run `bash start_mac_linux.sh` from a terminal.
3. Open **http://localhost:5173**. Keep the two server terminals open.
4. Upload a JPG/PNG/WebP photo, type a prompt, choose style(s), and click **Generate**.

By default the app starts in **DEMO mode**: it creates *local graphic templates* (not AI images), without any account, external service, or charge. It is fully interactive in demo mode. The folder `backend/data/` is created automatically and contains the SQLite database and media files.

### Enable real OpenAI image generation

In `backend/.env` (copied automatically from `.env.example`), change:

```dotenv
GENERATOR_BACKEND=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_QUALITY=high
```

Restart the backend. Real image generation uses the OpenAI **Images edit API** and your uploaded reference picture. **You need a billed OpenAI API account with model access; ChatGPT subscriptions do not include API credit.** Live requests incur charges. The demo is not real AI and is deliberately labeled as such.

### Enable ImageKit cloud storage (optional)

In `backend/.env`, change:

```dotenv
STORAGE_BACKEND=imagekit
IMAGEKIT_PRIVATE_KEY=your_private_key_here
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/YOUR_ID
```

Restart the backend. References and generated images will be uploaded to ImageKit. By default, storage is local and variants use Pillow to crop to exact dimensions. With ImageKit, variants use its smart-focus URL transformations so you do not regenerate images. The `IMAGEKIT_PRIVATE_KEY` is **server-only**. (The public key is unnecessary for this server-side upload flow.)

## Manual setup

**Terminal 1 — FastAPI**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — React**

```bash
cd frontend
npm install
npm run dev
```

- UI: http://localhost:5173
- REST API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health

## API & how it works

| Endpoint | Purpose |
| --- | --- |
| `POST /api/upload-headshot` | Multipart photo upload (`image` field); returns `reference_id` |
| `POST /api/jobs` | JSON `{ "prompt": "...", "reference_id": "...", "styles": ["bold", "minimal"] }` |
| `GET /api/jobs` | Recent projects |
| `GET /api/jobs/{id}` | Full job and each thumbnail status |
| `GET /api/jobs/{id}/events` | SSE `job_update` / `job_completed` |
| `GET /api/thumbnails/{id}/image/{variant}` | Local original/youtube/shorts/square image |
| `GET /api/styles` | Style presets |

Server workflow: **image validation → reference upload → SQLite job → bounded asyncio workers → image generation → image storage → job status updates → SSE to React → responsive export URLs**. Each thumbnail has its own failure state so partial success is preserved. Work interrupted by a restart is retried. The browser uses `EventSource`, not repeated fetch polling.

## Test the project

```bash
cd backend
python -m pytest -q
```

Tests exercise upload validation, queued 2-style generation, SSE, database persistence, and exact image export dimensions **without API keys**. Frontend production build: `cd frontend && npm run build`.

## Notes / limitations

- **Local learning/portfolio project, not internet-deployment ready.** There is **no authentication, account isolation, rate limiting, CSRF policy for authenticated workflows, or user media access control**. Do not expose it publicly without adding those safeguards.
- Run one backend process (`uvicorn ...`, **not** `--workers 4`); the job queue is in-process. For multi-instance deployments migrate to Redis/Celery/RQ or another shared queue. SQLite is intended for local development.
- Uploads must be JPG, PNG or WebP; default maximum is 8 MB. Stored images are normalized to JPEG before passing them to the image editor. The backend never downloads arbitrary user URLs.
- Files in `backend/data/` may contain private uploaded photos. They are intentionally excluded from Git and from this ZIP.
- Real API output depends on model availability and generation quality; image text and exact likeness are not guaranteed. OpenAI or ImageKit credentials cannot be verified by offline tests.
- The project follows the tutorial's architecture. The DB layer uses **SQLAlchemy 2.x ORM directly** (SQLModel is built on this ORM), so it can be reliably tested with the installed environment. Image generation uses the direct Images edit endpoint rather than the tutorial's Responses tool; both are supported patterns for this goal.
- Real image generation and remote storage features are implemented but cannot be end-to-end verified without *your* API keys.

See `.env.example` for every setting. Source is organized into `frontend/src` and `backend/app` with comments explaining the workflow.
