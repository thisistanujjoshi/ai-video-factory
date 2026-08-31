# AI Video Factory

Automates short-form video production end to end: research, idea generation,
scripting, storyboarding, asset generation, narration, rendering, QA, human
approval, publishing (YouTube Shorts, Instagram Reels, TikTok), analytics,
and strategy learning.

Full design in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Current build
progress in [BUILD_STATUS.md](BUILD_STATUS.md).

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
