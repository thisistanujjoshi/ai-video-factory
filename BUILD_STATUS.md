# Build Status

## Phase 0 — Foundation

**Status:** Complete

**Implemented:**
- Repository structure per the target layout (backend modules, frontend
  placeholder, prompts/, content_profiles/, storage/, docs/).
- FastAPI app (`backend/app/main.py`) with `GET /api/v1/health`, reporting
  Postgres and Redis connectivity independently without crashing when either
  is unreachable.
- SQLAlchemy engine/session setup (`backend/app/database/`) reading
  `DATABASE_URL` from env.
- Celery app (`backend/app/workers/celery_app.py`) wired to `REDIS_URL`,
  with a `ping` task.
- Alembic migration environment, wired to the same settings object as the
  app (no duplicated DB URL config). No models/migrations yet — nothing to
  migrate until Phase 1.
- `.env.example` covering every env var named in the spec, even ones unused
  until later phases (provider keys, publishing client IDs), so later
  phases don't need to touch this file.
- `docker-compose.yml`: postgres, redis, backend, worker services.
- Test suite (pytest): config loads with defaults, health endpoint returns
  200 with expected shape.
- Lint/format/typecheck clean: ruff, black, mypy.

**Tests:** 2 passed, 0 failed (`uv run pytest` in `backend/`).

**Known limitations:**
- `docker compose up` — **IMPLEMENTED, NOT LIVE TESTED**. No Docker daemon
  in this environment. Compose file is written and should work; verify with
  `docker compose up --build` + `curl localhost:8000/api/v1/health` before
  trusting it in a real deploy.
- No Postgres/Redis available locally either, so "database connection
  works" / "worker connects to Redis" acceptance criteria are verified only
  via the health endpoint's graceful-degradation path (it reports the
  connection error, doesn't crash) — not against a live instance.

**Next task:** Phase 1 — content profiles, research/idea/script/storyboard
models, idea generation + scoring with mock LLM provider.

## Phase 1 — Content System

**Status:** Complete

**Implemented:**
- Models: `ContentProfile`, `ResearchItem`, `Idea`, `Script`, `Video`,
  `Scene`, `AgentRun`. Nested profile config (niche/audience/video/style/
  strategy/publishing/schedule) stored as JSON columns, validated at the API
  boundary by `app/schemas/content_profile.py` — see the `ponytail:` note in
  `app/models/content_profile.py` for the normalize-later tradeoff.
- Explicit `VideoState` enum (`app/models/video_state.py`) with a
  transition table; invalid transitions raise `InvalidStateTransition`.
- `LLMProvider` abstraction (`app/providers/llm.py`) + `MockLLMProvider`,
  selected via `LLM_PROVIDER` (defaults to `mock`). Mock returns canned,
  schema-shaped JSON per `mode` (`ideas`/`script`/`storyboard`) — no
  network calls, no spend.
- `IdeaAgent`, `ScriptAgent`, `StoryboardAgent` — each: builds a prompt from
  `/prompts/<agent>/v1.txt`, calls the LLM, validates the JSON response
  against a Pydantic schema (one retry on malformed JSON, never silently
  accepted), and records an `AgentRun` row (provider/model/prompt_version/
  input/output/status/duration) either way.
- Idea scoring (`app/services/idea_scoring.py`): weighted sum of six
  component scores per spec section 13; weights verified against the
  spec's own worked example (91/82/75/90/87/70 → 83.95).
- Idea dedup: exact normalized-title matching (see `ponytail:` note in
  `app/agents/ideas/agent.py` — semantic/embedding dedup is section 37,
  a separate later feature).
- API: full CRUD on `/api/v1/content-profiles`; `POST /api/v1/ideas/generate`,
  `GET /api/v1/ideas`, `GET /api/v1/ideas/{id}`; `POST /api/v1/videos/generate`
  (idea → script → storyboard, synchronously — see `ponytail:` note in
  `app/api/videos.py` for why this isn't a Celery job yet), `GET /api/v1/videos`,
  `GET /api/v1/videos/{id}`.
- Alembic migration `62aab4f180b6` creates all 7 new tables with correct FK
  ordering and a native Postgres enum for `videos.state`.
- Example content profile YAML (`content_profiles/dark_mysteries.yaml`) —
  reference only, not auto-loaded (no consumer needs that yet).
- Tests: idea scoring formula, video state transitions (valid + invalid),
  mock provider output against each schema, and a full end-to-end pipeline
  test (content profile → generate ideas → generate video → assert
  `storyboard_ready` with populated scenes) — this is the Phase 1 acceptance
  criterion, exercised through the real HTTP API.

**Tests:** 9 passed, 0 failed (`uv run pytest` in `backend/`). Ruff, black,
mypy all clean.

**Known limitations:**
- Migration was authored and applied against a throwaway local SQLite DB
  (still no Postgres available in this environment) — **IMPLEMENTED, NOT
  LIVE TESTED** against real Postgres. Re-run `alembic upgrade head` against
  a live Postgres instance before trusting it in a deploy.
- No `ResearchAgent` yet — `ResearchItem` the DB model exists (Phase 1 spec
  bullet), and `IdeaAgent` accepts an optional research item, but nothing
  currently produces one. Add when research-driven ideation is actually
  needed.
- `/videos/generate` runs the idea→script→storyboard pipeline synchronously
  in the request handler, not via Celery. Fine while the LLM is mocked and
  instant; revisit when Phase 2 adds real (slow) asset generation/rendering.

**Next task:** Phase 2 — asset provider abstraction + mock, TTS abstraction
+ mock, captions, FFmpeg rendering, video model additions for the render
pipeline.
