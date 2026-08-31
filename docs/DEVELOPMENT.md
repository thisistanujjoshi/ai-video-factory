# Development

## Setup

```bash
cp .env.example .env
cd backend
uv venv
uv pip install -e ".[dev]"
```

## Run

With Docker (starts Postgres + Redis too):

```bash
docker compose up --build
```

Without Docker, against your own Postgres/Redis (or none — `/health`
degrades gracefully instead of crashing):

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Worker:

```bash
cd backend
uv run celery -A app.workers.celery_app worker --loglevel=info
```

## Test / lint / typecheck

```bash
cd backend
uv run pytest
uv run ruff check .
uv run black --check .
uv run mypy app
```

Or via `make test` / `make lint` / `make fmt` from the repo root.

## Migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

`alembic/env.py` reads `DATABASE_URL` from `app.config.get_settings()`, so
it stays in sync with the app's own config — no separate URL to maintain.

## Environment without Docker/Postgres/Redis installed

The health endpoint (`GET /api/v1/health`) never hard-fails on missing
infra: it reports `"database": "error: ..."` / `"redis": "error: ..."` per
component and an overall `"degraded"` status instead of raising. This is
what let Phase 0 be built and tested on a machine with no Docker daemon —
confirm real connectivity via `docker compose up` + `curl` once Docker is
available.

## Generating a migration without a live Postgres

`alembic revision --autogenerate` needs to connect to `DATABASE_URL` to
diff against the current schema. Without Postgres running, point it at a
throwaway SQLite file instead — the generated migration (create_table /
add_column DDL via `op.*`) is dialect-portable:

```bash
cd backend
DATABASE_URL="sqlite:///./_migration_gen.db" uv run alembic revision --autogenerate -m "message"
DATABASE_URL="sqlite:///./_migration_gen.db" uv run alembic upgrade head  # sanity check it applies
rm _migration_gen.db
```

Re-run `alembic upgrade head` against real Postgres before trusting the
migration in a deploy.
