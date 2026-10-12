# Quick Setup — Framecraft Thumbnail Studio

**Requirements:** Python 3.11+ and Node.js 20+ (internet for initial setup).

1. Unzip this project.
2. On **Windows**, double-click `start_windows.bat`.
   On **macOS/Linux**, run `bash start_mac_linux.sh`.
3. Open **http://localhost:5173** in your browser.
4. Upload a photo, enter a video idea, select 1–3 styles and click **Generate**.

The app works immediately in **demo mode** (locally generated templates, **not AI**).

**To enable real AI:** edit `backend/.env`:

```env
GENERATOR_BACKEND=openai
OPENAI_API_KEY=your_key_here
```

Restart the backend. OpenAI API usage costs money and requires API access.

**Optional ImageKit CDN:** set `STORAGE_BACKEND=imagekit`, `IMAGEKIT_PRIVATE_KEY` and `IMAGEKIT_URL_ENDPOINT` in the same `.env`, then restart.

**Backend:** http://127.0.0.1:8000/docs  •  **Frontend:** http://localhost:5173

**Run tests:** `cd backend` then `python -m pytest -q` (inside the virtual environment).

See `README.md` for manual setup, architecture and security notes. Do not deploy publicly without authentication and rate limits.
