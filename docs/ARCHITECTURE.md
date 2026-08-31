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
concrete implementations are selected via env vars (`LLM_PROVIDER`, etc.),
unset/`mock` by default. Mock providers shipped first (Phases 1-2) so the
whole pipeline was testable without API keys or spend before any real
vendor existed — real providers are added without touching call sites.
`GeminiLLMProvider` and `GeminiImageProvider` (Phase 5, `app/providers/
llm.py` / `image.py`) are the first real implementations, both using
Google's `google-genai` SDK. Structured output doesn't go through a
vendor-specific schema type: `generate_structured()`
(`app/agents/base.py`) hands every provider the caller's Pydantic
`response_model.model_json_schema()` as-is via a `response_schema` kwarg —
Gemini's `response_json_schema` accepts the Pydantic-shaped JSON Schema
subset ($defs/$ref, minimum/maximum, etc.) directly, so no translation
layer was needed; a provider that can't use it just ignores the kwarg.

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

## Video rendering (Phase 2)

Pure ffmpeg, no LLM involvement (Rule 4). Per scene: a still image
(`ImageProvider`) + a voiceover clip (`TTSProvider`) become one `.mp4`
segment; segments concatenate; captions burn in from an SRT built directly
from each scene's known `caption` text and `duration_seconds` (no ASR --
see the `ponytail:` note in `app/video/captions.py`, real per-word timing
arrives with a real TTS provider in Phase 5). `libopenh264` is the H.264
encoder in use, not `libx264` -- this environment's ffmpeg build has no
software `libx264` (patent-restricted distro packaging), only hardware
H.264 encoders plus `libopenh264`; swap `VIDEO_CODEC` in
`app/video/renderer.py` if deploying somewhere `libx264` is available.

## Deliberately deferred

- Frontend: directory exists, nothing built until Phase 4 (dashboard needs
  something to display first).
- Agents, workflows, models, schemas, services, providers, integrations,
  video, storage modules: directories scaffolded per the target structure,
  implementations land with the phase that needs them (Phase 1 onward).
- Publishing/analytics/learning: architected for (module boundaries exist)
  but not implemented until their respective phases.
