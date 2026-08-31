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

## Phase 2 — Production

**Status:** Complete

**Implemented:**
- `StorageProvider` abstraction (`app/storage/`) + `LocalStorageProvider`
  (dev implementation, writes under `storage/`, gitignored).
- `ImageProvider`/`MockImageProvider` (`app/providers/image.py`) — a
  solid-color PNG per scene via ffmpeg's `lavfi` color source, colored
  deterministically from the scene's `visual_prompt` text. No image-gen API
  key, no new dependency.
- `TTSProvider`/`MockTTSProvider` (`app/providers/tts.py`) — silent WAV of
  the scene's exact `duration_seconds` via ffmpeg's `anullsrc`. No TTS API
  key, no new dependency.
- `Asset` / `AudioAsset` models, one row per generated scene image /
  voiceover, with provider/source/path recorded.
- Captions (`app/video/captions.py`): SRT built directly from each scene's
  known caption text + duration — no ASR step (see the `ponytail:` note
  there for why that's the correct simplification here, not a shortcut).
- Renderer (`app/video/renderer.py`): per-scene ffmpeg encode → concat →
  caption burn-in → final MP4, `libopenh264`/`aac`, target resolution from
  the content profile. Pure deterministic code, zero LLM calls.
- `produce_video` service (`app/services/production.py`) orchestrates the
  above: ASSETS_GENERATING → ASSETS_READY → RENDERING → RENDERED (or
  FAILED on any error, with rollback).
- API: `POST /api/v1/videos/{id}/render` (409 if the video isn't
  `storyboard_ready`).
- Alembic migration `ba1d88ad72fb`: `assets`, `audio_assets` tables,
  `videos.rendered_path` column.

**Tests:** 12 passed, 0 failed. Notably — **this environment has real
ffmpeg installed**, so unlike Phase 0/1's Postgres/Redis/Docker gaps, Phase
2's core acceptance criterion is verified for real, not just structurally:
- `test_renderer.py`: renders two synthetic scenes end-to-end, `ffprobe`
  confirms a real H.264/AAC MP4 with the requested duration.
- `test_production_pipeline.py`: drives the full HTTP API (content profile
  → ideas → video → storyboard → render) and `ffprobe`s the actual output
  file the API reports; also checked manually — a 7-scene render produced a
  320x568 h264/aac MP4, ~42s duration (7 × 6s scenes), exactly as expected.

**Known limitations:**
- No `libx264` in this ffmpeg build (see `docs/ARCHITECTURE.md`) — using
  `libopenh264` instead. Works, but re-verify encoder choice if deploying
  to an environment with different ffmpeg codec support.
- Rendering runs synchronously in the request handler, same tradeoff noted
  in Phase 1 for `/videos/generate` — becomes a real problem once assets
  are large/slow (real image/TTS providers) or scenes need to render in
  parallel; that's when this moves to a Celery job (spec section 24).
- No resume-from-last-completed-scene on failure yet (spec section 57) —
  a failed render currently rolls back and marks the whole video FAILED.
  Worth adding once retries on partial failures are actually observed.

**Next task:** Phase 3 — technical QA checks (file/codec/resolution/
duration/caption validation), AI QA (LLM content review via the mock
provider), QA scoring, rejection + regeneration hooks.

## Phase 3 — QA

**Status:** Complete

**Implemented:**
- Technical QA (`app/video/qa_checks.py`, pure code + `ffprobe`/`ffmpeg`,
  no LLM): file exists/non-empty, valid container, video+audio streams
  present, resolution matches the profile, aspect ratio matches (with
  tolerance), codecs are h264/aac, duration within the profile's
  min/max (±2s encode-rounding tolerance), every scene has caption text,
  and a decode pass (`ffmpeg ... -f null -`) to catch corrupt frames.
- AI QA (`QAAgent`, `app/agents/qa/`): same generate→validate→retry→log
  pattern as the other agents, reviews hook/narrative/pacing/captions/
  platform fit, returns `{approved, score, issues, recommendations}`. Mock
  LLM always approves (score 88) — see the `ponytail:` note in
  `app/providers/llm.py` for why: there's nothing genuinely bad about
  canned mock content for a content review to catch, so Phase 3's
  automatic-rejection tests exercise the *technical* checks instead, which
  are deterministic and don't depend on LLM behavior.
- QA orchestration (`app/services/qa.py`): `RENDERED → QA_PENDING →
  AWAITING_APPROVAL | QA_FAILED`, gated on technical pass AND AI approval
  AND score ≥ `QA_SCORE_THRESHOLD` (70 — also earmarked for the Phase 9
  autonomous-publish gate, spec section 52).
- API: `POST /api/v1/videos/{id}/qa` (409 unless `rendered`), `POST
  /api/v1/videos/{id}/regenerate` (409 unless `qa_failed`; regenerates the
  storyboard and returns to `storyboard_ready` — see the `ponytail:` note
  in `app/api/videos.py` on why this is whole-storyboard, not per-scene,
  regeneration).

**Tests:** 19 passed, 0 failed. `test_qa_checks.py` builds real MP4s via
ffmpeg and asserts pass/fail on real `ffprobe` output.
`test_qa_pipeline.py` drives the full HTTP pipeline twice with different
profile duration bounds against the same 42s mock render — once
producing `qa_failed` (bounds exclude 42s) and once `awaiting_approval`
(bounds include it) — proving automatic rejection is real, not asserted
in isolation. Also covers regenerate's state-guard and 409s on
out-of-order calls (`qa` before `render`, `regenerate` when not
`qa_failed`).

**Known limitations:**
- No dedicated QA-results table — technical issues and the AI QA verdict
  are returned in the `/qa` response and logged via the `qa_agent`
  `AgentRun` row, but not otherwise persisted for later display. Add a
  table if the Phase 4 dashboard needs to show QA history, not just the
  latest outcome.
- Regeneration is whole-storyboard only (see above) — no way yet to
  identify or redo a single bad scene.
- No human approve/reject endpoints yet — those are Phase 4 (dashboard +
  approval UI); `AWAITING_APPROVAL`/`REJECTED`/`APPROVED` states already
  exist in the state machine (Phase 1) and are exercised by nothing until
  then.

**Next task:** Phase 4 — dashboard: content profile UI, ideas UI, video
queue, video preview, approval, regeneration.

## Phase 4 — Dashboard

**Status:** Complete

**Implemented:**
- Backend: `POST /api/v1/videos/{id}/approve` and `/reject`
  (`awaiting_approval → approved|rejected`), `GET /api/v1/videos/{id}/file`
  (streams the rendered MP4 by `rendered_path`), CORS opened for
  `localhost:3000`.
- Frontend (`frontend/`, Next.js 16 App Router + TypeScript + Tailwind, no
  UI/state-management library — plain `fetch` + `useState`/`useEffect`,
  client components throughout since this is an operator dashboard, not a
  content site needing SSR/SEO): `/dashboard`, `/content-profiles`,
  `/content-profiles/[id]` (view + generate ideas), `/ideas` (generate
  video from an idea), `/videos`, `/videos/[id]` (script/scenes, QA report,
  state-gated action buttons — render/QA/approve/reject/regenerate — and an
  embedded `<video>` preview once rendered), `/queue` (videos bucketed by
  state, client-side). `/publishing` and `/analytics` are honest
  placeholders naming the phase that implements them (Rule 1: never claim
  a placeholder is complete); `/settings` is a read-only reference of
  provider env vars — there's no settings API yet.
- `lib/api.ts`: one typed client mirroring the backend's Pydantic schemas,
  used by every page.

**Tests:** Backend 23/23 passing (added `test_approval.py` for
approve/reject/file). Frontend: `npm run lint` and `npm run build` both
clean (TypeScript strict, all 12 routes compile — 10 static, 2 dynamic for
the `[id]` routes).

**Verification:** Both dev servers were actually started (`uvicorn` against
a throwaway SQLite DB migrated via Alembic, `next dev`) and the full golden
path was driven with `curl` using the exact endpoints/payloads the frontend
calls: create profile → generate ideas → generate video → render → QA →
approve, plus a CORS preflight check confirming the browser could make
these calls from `localhost:3000`. **Not verified**: actual interactive
browser click-through — no browser-automation tool was connected in this
session (the `claude-in-chrome` skill exists but its underlying tools
weren't registered here). The API contract and page compilation are
confirmed; visual/interactive behavior (form validation feel, button
states, video playback) is not. Worth a manual pass or a Playwright test
(spec section 46 mentions Playwright for exactly this) before relying on
this as fully user-verified.

**Known limitations:**
- No auth — anyone who can reach the API can do anything. Fine for local
  MVP use; spec section 44 (auth/authorization) is unaddressed until a
  phase that actually needs it.
- `/queue` derives its buckets from `GET /videos` client-side; no backend
  job-queue/progress endpoint (matches the "no Celery yet" tradeoff noted
  in Phases 1-2 — becomes real once the pipeline is actually async).
- No edit form for an existing content profile (create + view only); add
  if that turns out to be needed rather than always creating a new one.

**Next task:** Phase 5 — real AI provider implementations, added behind
the existing provider abstractions (mocks stay as the default/fallback).
Needs API keys from the user to live-test; will implement the interfaces
and configuration regardless per Rule 1, and mark live-testing status
honestly.

## Phase 5 — Real AI Providers

**Status:** Partial (LLM live-verified; image implemented, not live-testable
with the available key; TTS/video providers not started this phase)

**Implemented:**
- `google-genai>=1.0` added as a backend dependency.
- `GeminiLLMProvider` (`app/providers/llm.py`): async, uses Gemini's
  `response_json_schema` for schema-constrained decoding — takes the
  caller's Pydantic schema unmodified (see ARCHITECTURE.md). Selected via
  `LLM_PROVIDER=gemini` + `LLM_API_KEY`.
- `GeminiImageProvider` (`app/providers/image.py`): same SDK, image-capable
  model. Selected via `IMAGE_PROVIDER=gemini` + `IMAGE_API_KEY`.
- `generate_structured()` now always passes `response_schema` to whatever
  provider is configured (mock ignores it, real providers use it) — a
  one-line change to the shared helper, not per-agent.
- Mocks are untouched and remain the default — `LLM_PROVIDER`/
  `IMAGE_PROVIDER` unset behaves exactly as before.

**Live-tested (2026-08-31, real Google AI Studio key, key never committed
or written to any file — env var only):**
- `GeminiLLMProvider` — **IMPLEMENTED, LIVE TESTED.** Plain text generation
  works (~29s on `gemini-flash-lite-latest` first call); schema-constrained
  JSON generation is fast (1-2s) and round-trips through Pydantic
  validation correctly, including against our actual nested schemas
  (`GeneratedIdeaList` with `$defs`, `ge`/`le` constraints). The full
  idea→script→storyboard→QA pipeline was run against the real API directly
  (`test_gemini_e2e_pipeline.py`) and passed in ~9s.
  - Model note: `gemini-2.5-flash` returned 404 ("no longer available to
    new users") on this key/date; `gemini-3.6-flash` (the API's own
    suggested replacement) worked for plain text (~29s) but consistently
    timed out (504/499) on schema-constrained requests even at 55s+.
    `gemini-flash-lite-latest` is fast and reliable for both — that's the
    default `model_name`. If this regresses, re-run
    `client.models.list()` to see what's current; don't assume model names
    from any point in time stay valid.
- `GeminiImageProvider` — **IMPLEMENTED, NOT LIVE TESTED.** A real call to
  `gemini-3.1-flash-image` returned `429 RESOURCE_EXHAUSTED`: "Quota
  exceeded ... limit: 0" for every free-tier image-generation metric on
  this key. This is a confirmed account/tier limitation, not a guessed
  one — the code path is implemented per Rule 1 but unverified end-to-end.
  Re-test once a key with image quota (paid tier, or a different project)
  is available.

**Tests:** 25 passed, 2 skipped (`test_gemini_provider.py`,
`test_gemini_e2e_pipeline.py` — both skip via `pytest.mark.skipif` when
`GEMINI_API_KEY` isn't in the environment, so CI/normal runs are
unaffected). Both passed live. `test_generate_structured.py` added to
cover the `response_schema`-passing and retry-on-malformed-JSON behavior
directly (previously only exercised indirectly through mock-based agent
tests). Ruff/black/mypy clean.

**Known limitations:**
- TTS and Video providers: interfaces exist (`TTSProvider` since Phase 2),
  no real implementation yet — deferred, not attempted this pass (the user
  chose to scope Phase 5 to LLM + image with the one key available; TTS
  needs a different vendor).
- `GeminiImageProvider` doesn't request a specific resolution (the
  `generate_content` image API doesn't expose width/height the way the
  mock does) — relies on the renderer's existing scale step, untested
  against a real non-matching-aspect-ratio image (see the `ponytail:` note
  in `app/providers/image.py`).
- No provider fallback chain (spec section 39: primary → fallback on
  failure) — still just a single configured provider, mock or real.

**Next task:** Phase 6 — publishing (Publisher interface, YouTube/
Instagram/TikTok integrations, scheduling). Real platform credentials
needed for live testing; will implement interfaces + mocked integration
tests regardless per Rule 1.

## Phase 6 — Publishing

**Status:** Complete (interfaces + mock; real platform APIs are
documented stubs — no OAuth credentials available, per Rule 1)

**Implemented:**
- `Publication` model (`video_id`+`platform` unique — idempotent by
  construction, spec section 58) with `PublicationStatus` enum, per-
  platform metadata JSON, scheduling/publish timestamps, `platform_ref`,
  error, retry_count.
- `Publisher` ABC (`app/integrations/base.py`): `publish`/`schedule`/
  `get_status`. `MockPublisher` is the default for every platform via
  `get_publisher()` — realistic async behavior, and a `fail_times` knob
  used to test the retry path without a real flaky API.
- `YouTubePublisher`, `InstagramPublisher`, `TikTokPublisher`
  (`app/integrations/{youtube,instagram,tiktok}/`): real classes exist,
  each documents the actual upload flow for that platform (YouTube
  resumable `videos.insert`; Instagram Graph API container→publish;
  TikTok Content Posting API init→upload→poll) and raises
  `NotImplementedError` — every one needs an interactive OAuth consent
  flow this backend has no UI for, which the `client_id`/`client_secret`
  pair alone (from `.env`) can't substitute for. Swapping one in is a
  one-line change in `get_publisher()`.
- `app/services/publishing.py`: `build_platform_metadata()` (deterministic
  — packages existing script/idea content into YouTube's title/
  description/tags vs. Instagram/TikTok's caption/hashtags shape, not an
  LLM call, see its docstring for why), `publish_video()` and
  `schedule_video()` — both idempotent per platform, `publish_video()`
  retries transient failures with real (if short) exponential backoff
  before marking a platform `FAILED`.
- API: `POST /api/v1/videos/{id}/schedule`, `POST /api/v1/videos/{id}/
  publish`, `GET /api/v1/videos/{id}/publications`.
- Alembic migration `9db6640f6afb`: `publications` table.

**Tests:** 37 passed, 2 skipped (unrelated Gemini live tests). New:
`test_publishing.py` (metadata shape, idempotency, retry-then-succeed,
retry-exhaustion→FAILED, scheduling, and all three real publishers
confirmed to raise `NotImplementedError`) and `test_publishing_api.py`
(full HTTP flow: approve → publish → 3 platforms published; approve →
schedule → publish; publish-before-approval rejected with 409).

**Known limitations:**
- No real platform integration is live — all three need an OAuth consent
  UI this project doesn't have yet. This was a scoping choice (Phase 5's
  one available key doesn't cover any of these platforms), not an
  oversight; the interfaces are real and ready for whoever builds that
  flow.
- Publishing runs synchronously in the request handler, same tradeoff as
  every other pipeline step so far — becomes a real Celery job once a
  real publisher's upload latency (and the need to actually fire at a
  scheduled time, not just record one) makes that necessary.
- Video-level state is PUBLISHED/FAILED as an aggregate across platforms;
  a partial failure (2 of 3 platforms succeed) marks the video FAILED
  even though the successful `Publication` rows stay PUBLISHED and are
  not retried. Query `/publications` for the real per-platform picture.

**Next task:** Phase 7 — analytics: metrics model, platform collectors
(mocked, same reasoning as publishing), normalized metrics, analytics
dashboard.

## Phase 7 — Analytics

**Status:** Complete (mocked collectors — same OAuth gap as Phase 6's
publishers, no real platform account connected)

**Implemented:**
- `Metric` model: one row per collected snapshot of one `Publication`.
  Normalized columns (views/likes/comments/shares/watch_time/retention/
  followers_gained/engagement_rate) are the common schema every platform
  maps into; `raw` keeps the platform's own payload separately (spec
  section 33).
- `AnalyticsCollector` ABC (`app/integrations/analytics.py`) +
  `MockAnalyticsCollector` (deterministic per-publication fake numbers,
  no network) as the default for every platform via
  `get_analytics_collector()`. `YouTubeAnalyticsCollector`,
  `InstagramInsightsCollector`, `TikTokAnalyticsCollector` exist as real
  stubs documenting each platform's actual metrics API, raising
  `NotImplementedError` — identical pattern and identical reason
  (OAuth) as Phase 6's publishers.
- `app/services/analytics.py`: `collect_metrics_for_video()` (one
  snapshot per PUBLISHED platform, `engagement_rate` computed
  deterministically, not by the collector), `latest_metrics_for_video()`
  (most recent snapshot per publication), `sum_totals()`.
- API: `POST /api/v1/videos/{id}/analytics/collect?snapshot_label=...`,
  `GET /api/v1/analytics`, `GET /api/v1/analytics/videos/{id}`.
- Frontend: `/analytics` is now a real page (was a Phase-4/5 placeholder)
  — grand totals, per-video totals, per-platform snapshot list. Video
  detail page gets a "Collect analytics snapshot" action once `published`.
- Alembic migration `f425fea336e7`: `metrics` table.

**Tests:** 47 passed, 2 skipped (unrelated Gemini live tests). New:
`test_analytics.py` (mock collector determinism, one metric per published
platform, unpublished platforms skipped, latest-snapshot-wins, totals
math, all three real collectors confirmed `NotImplementedError`) and
`test_analytics_api.py` (full HTTP flow: publish → collect → per-video
and overall `/analytics` both reflect it; empty-state video returns zero
totals, not an error).

**Known limitations:**
- No automatic scheduled collection at 1h/6h/24h/48h/7d (spec section
  34) — `/analytics/collect` is triggered on demand (dashboard button, or
  an external cron hitting the endpoint with the right `snapshot_label`).
  Real scheduling needs Celery beat, which nothing in this project has
  wired up yet — same gap as every other "should be a background job"
  note in this file.
- No real platform account connected (same reason as Phase 6) — numbers
  are plausible-looking mock data, not real performance.
- No correlation/causation analysis (spec section 35, "Question hooks:
  average retention = X" style comparisons) — that's Phase 8 (Learning),
  which needs a real history of metrics across many videos to be
  meaningful; this phase only stores and displays snapshots.

**Next task:** Phase 8 — learning: performance analysis, content pattern
analysis, strategy generation/storage, content memory (semantic duplicate
detection).
