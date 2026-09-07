# AI Video Factory

An end-to-end pipeline that turns a content niche into a published short-form
video with no manual editing: research a trending topic, generate an idea,
write a script, storyboard it into scenes, generate visuals and narration for
each scene, render with ffmpeg, run automated QA, get human approval on a
dashboard, then publish to YouTube Shorts / Instagram Reels / TikTok — with
analytics feeding back into what gets picked next time.

```
Content Profile → Research → Ideation → Scripting → Storyboard →
Assets → Voiceover → Captions → Render (ffmpeg) → QA → Approval →
Schedule → Publish → Analytics → Strategy → (feeds back into Ideation)
```

Every AI vendor (LLM, image, video, TTS) sits behind a provider interface
selected via env vars, defaulting to a mock — so the whole pipeline runs and
is fully testable with zero API keys and zero spend before any real provider
exists. Real Gemini-backed LLM, image, and TTS providers are implemented and
live-verified; a real Veo video provider is implemented but not yet
live-tested (quota-gated) — see [BUILD_STATUS.md](BUILD_STATUS.md) for
exactly what's verified vs. implemented-only.

Full design in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Current build
progress, phase-by-phase, in [BUILD_STATUS.md](BUILD_STATUS.md).

## Stack

Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery.
Frontend: Next.js (App Router), React, TypeScript, Tailwind — `frontend/`.
Video: FFmpeg.

## Quickstart (Docker)

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/api/v1/health
```

## Quickstart (local, no Docker)

Requires `uv`. Point `DATABASE_URL`/`REDIS_URL` in `backend/.env` at
Postgres/Redis instances you run yourself (or skip — `/health` reports
`degraded` instead of failing when they're unreachable).

```bash
cd backend
uv venv && uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload
```

## Dashboard

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev   # http://localhost:3000
```

Needs the backend running (see above) — the dashboard talks to it directly
from the browser, no server-side proxy.

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for running tests, lint,
migrations, and the worker.
