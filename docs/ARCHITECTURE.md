# Architecture

## Shape

A modular monolith, not microservices. One FastAPI app, one Celery worker
pool, one Postgres database, one Redis instance for broker + cache. Modules
inside `backend/app/` are separated by responsibility (agents, providers,
video, integrations, ...) so pieces can be extracted into services later if
scale ever demands it — but nothing is split prematurely.

## Core pipeline

```
Content Profile → Research → Ideation → Scripting → Storyboard →
Assets → Voiceover → Captions → Render (ffmpeg) → QA → Approval →
Schedule → Publish → Analytics → Strategy → (feeds back into Ideation)
```

Each arrow is a Celery job. Jobs write state transitions to Postgres so a
crash mid-pipeline resumes from the last completed stage instead of
restarting the whole video (this lands in Phase 2+, once there's a video
model with stages to resume).

## Provider abstraction

Nothing calls a specific AI vendor directly. `app/providers/` defines
interfaces (`LLMProvider`, `ImageProvider`, `VideoProvider`, `TTSProvider`);
concrete implementations (mock, then real vendors) are selected via env vars
(`LLM_PROVIDER`, etc.) in Phase 5. Mock providers ship first so the whole
pipeline is testable without API keys or spend — real providers are added
without touching call sites.

## State machine

Videos move through an explicit enum of states (DRAFT → ... → PUBLISHED /
FAILED / REJECTED). Invalid transitions are rejected at the model layer, not
scattered `if` checks in callers. Implemented in Phase 1 alongside the video
model.

## Data vs. media

Postgres holds metadata, relationships, state, and metrics. Media files
(images, audio, video, captions) go through a `StorageProvider` abstraction
— local filesystem in development, swappable for object storage later.

## Why this order (build phases)

Foundation (this phase) → content generation → rendering → QA → dashboard →
real AI providers → publishing → analytics → learning → autonomous mode.
Each phase produces working, tested software; nothing later is assumed to
exist yet. See `BUILD_STATUS.md` for what's actually done vs. planned.

## Deliberately deferred

- Frontend: directory exists, nothing built until Phase 4 (dashboard needs
  something to display first).
- Agents, workflows, models, schemas, services, providers, integrations,
  video, storage modules: directories scaffolded per the target structure,
  implementations land with the phase that needs them (Phase 1 onward).
- Publishing/analytics/learning: architected for (module boundaries exist)
  but not implemented until their respective phases.
