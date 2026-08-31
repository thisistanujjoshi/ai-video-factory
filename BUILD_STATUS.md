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

## Phase 8 — Learning

**Status:** Complete

**Implemented:**
- `compute_patterns()` (`app/services/strategy.py`): pure aggregation, no
  LLM — averages engagement/retention (from Phase 7's latest metric per
  publication) grouped by `target_emotion` (the closest stored stand-in
  for "hook type" — no such column exists on `Idea`, see its docstring),
  duration bucket (short/medium/long relative to the profile's own
  min/max), and platform, each with a sample size so small buckets are
  visibly small (spec section 35: correlation, not causation).
- `StrategyAgent` (`app/agents/strategy/`): same generate→validate→
  retry→log pattern as every other agent, reasons over the computed
  patterns into `{best_topics, best_hook_types, recommended_duration,
  recommended_pacing, recommended_posting_windows, avoid_patterns,
  rationale}` (spec section 36), explicitly instructed not to overstate
  confidence from small samples.
- `ContentStrategy` model — one row per generation, history kept (not
  overwritten); `GET .../strategy` returns the latest.
- **The strategy actually changes future idea generation, verifiably**:
  `IdeaAgent` takes an optional `strategy` param and folds
  `best_topics`/`best_hook_types`/duration/pacing/`avoid_patterns` into
  the prompt (bumped to `prompts/ideas/v2.txt`); `/ideas/generate`
  fetches the profile's latest strategy automatically.
  `test_strategy_integration.py` proves this directly with a recording
  fake LLM provider that captures the actual prompt text — not just that
  a strategy object exists somewhere unused.
- `EmbeddingProvider` abstraction (`app/providers/embedding.py`):
  `MockEmbeddingProvider` is a hashing-trick bag-of-words vector — a real
  (if crude) technique, not random noise, and it genuinely catches
  lexical near-duplicates while leaving unrelated text alone (verified:
  0.92 similarity for reworded-but-same-story text, 0.08 for unrelated
  text). `GeminiEmbeddingProvider` exists — **IMPLEMENTED, NOT LIVE
  TESTED** this pass (verified the SDK call shape via inspection, didn't
  spend further live-API budget on the available key — see Phase 5).
- Content memory (`app/services/content_memory.py`, spec section 37):
  `IdeaAgent` embeds every surviving candidate and rejects (doesn't
  persist) anything cosine-similar ≥ 0.85 to an existing idea *on the
  same content profile* — a different profile can cover the same
  real-world story. Caught a real bug while wiring this up: the initial
  256-dim hashing space let two single-digit tokens collide into the
  same bucket and produce a false 1.0 similarity between distinct mock
  ideas, silently dropping a legitimate one — fixed by widening to
  4096 dims (see the comment on `EMBEDDING_DIM`).
- API: `POST /content-profiles/{id}/strategy/generate`, `GET .../strategy`.
- Frontend: profile detail page shows the current strategy (or offers to
  generate one) and regenerates it from history on demand.

**Tests:** 61 passed, 2 skipped (unrelated Gemini live tests). New:
`test_content_memory.py`, `test_strategy_computation.py` (aggregation
math against hand-built fixtures), `test_strategy_integration.py` (the
prompt-content proof above), `test_strategy_api.py`, `test_idea_dedup.py`
(near-duplicate rejected across separate `generate()` calls on the same
profile; a second profile is unaffected by the first's history).

**Known limitations:**
- "Hook type" pattern analysis uses `target_emotion` as a proxy — there's
  no field recording which of `profile.strategy.hook_types` an idea
  actually used. Add one if hook-type-specific learning turns out to
  matter more than emotion-based learning.
- No embedding-based similarity check on script/storyboard content, only
  ideas — matches spec section 37's own framing ("New Idea → Embedding →
  Similarity Search"), but a near-duplicate could still theoretically
  emerge later in the pipeline from two dissimilar ideas.
- `SIMILARITY_THRESHOLD = 0.85` is picked, not tuned, and calibrated
  against the mock's lexical-overlap scale — it will need re-tuning once
  a real (semantic) embedding provider is actually in use, since
  "0.85 cosine similarity" means something different for a transformer
  embedding than for a hashing-trick bag-of-words vector.

**Next task:** Phase 9 — autonomous mode: scheduled research → ideation →
production → QA → publishing → analytics → strategy loop, with
MANUAL/SEMI_AUTOMATIC/AUTONOMOUS safety modes per content profile (spec
section 52).

## Phase 9 — Autonomous Mode

**Status:** Complete (synchronous on-demand cycle, no real scheduler —
see limitations)

**Implemented:**
- `AutomationMode` enum (`manual`/`semi_automatic`/`autonomous`) as a
  first-class column on `ContentProfile`, **defaulting to `manual`** —
  new profiles never auto-run by accident (spec section 52's safety
  intent). Migration backfills existing rows to `manual` too (verified
  against a pre-existing row, not just an empty table — see the migration
  file's comment).
- Refactored idea→script→storyboard generation out of the `/videos/
  generate` endpoint into `app/services/pipeline.py` so both that
  endpoint and the new autonomous cycle share one implementation instead
  of two copies drifting apart.
- `run_autonomous_cycle()` (`app/services/autonomous.py`): ideas
  (research is skipped — no `ResearchAgent` exists, see Phase 1) →
  production → QA → for `AUTONOMOUS` only, auto-approve + auto-publish,
  gated by `can_auto_publish()` — AUTONOMOUS mode AND technical QA passed
  AND content approved AND score ≥ threshold AND no content issues,
  written out as separate explicit conditions (not just `outcome.passed`)
  because this is the one safety-critical decision in the whole system.
  `MANUAL` refuses to run at all (`AutomationDisabledError` → 409);
  `SEMI_AUTOMATIC` runs through QA and stops at `awaiting_approval`/
  `qa_failed` for a human.
- API: `POST /content-profiles/{id}/autonomous-cycle`. Frontend: profile
  detail page shows the mode, offers an automation-mode selector on
  create, and a "Run cycle now" button (disabled for `manual`) showing
  the outcome.

**A real bug, found and fixed via live manual testing** (not just unit
tests): running the cycle twice on the same profile crashed with an
unhandled 500. Cause: the mock LLM returns the *exact same* canned ideas
every call, so Phase 8's content-memory dedup correctly rejected 100% of
the second cycle's ideas as duplicates of the first cycle's — leaving
zero ideas and an unhandled `RuntimeError`. Fixed with a dedicated
`NoViableIdeasError` → clean `422` with an explanatory message, not a
workaround that reuses a stale idea (which would defeat dedup). This is
mock-specific — a real LLM varies output call to call — but the failure
mode is real regardless of provider, so the fix stands generally.
Re-verified live after the fix: same repeat-cycle call now returns 422
with a clear message instead of crashing.

**Tests:** 76 passed, 2 skipped (unrelated Gemini live tests). New:
`test_automation.py` (the `can_auto_publish` gate exhaustively — mode,
score, technical failure, content issues, each independently; all three
mode behaviors against a real render+QA pipeline; the repeat-cycle bug
fix), `test_automation_api.py` (same at the HTTP layer, plus the 409/422
status codes).

**Verified live** against a running server (not just the test suite): a
fresh `autonomous`-mode profile went from zero to a real rendered,
QA'd, auto-approved, auto-published video in one API call (~8.6s
end-to-end with the mock LLM/providers) — this is the Phase 9 acceptance
criterion in its most literal form, watched actually happen.

**Known limitations:**
- No real scheduler — "Scheduled Research" from the spec's Phase 9
  diagram doesn't exist; the cycle is synchronous and triggered on
  demand (dashboard button, or an external cron hitting the endpoint).
  Same Celery-beat gap noted throughout this project; wiring one up
  would make this genuinely autonomous rather than autonomous-when-asked.
- No `ResearchAgent` (Phase 1's own deferred item) — the cycle skips
  straight to ideation.
- One video per cycle call, not `schedule.videos_per_day` per day — that
  field exists on the profile but nothing reads it yet.
- The auto-publish gate has no separate "policy/risk flag" detector
  beyond what QA's content-review already produces (`content.issues`)
  — matches what the system actually has, but section 52's phrase
  "no policy/risk flags exist" could mean more (brand safety, platform
  ToS checks) in a fuller build.

**Final acceptance test (spec section 63):** every one of the 22 listed
steps has a working, tested path through this system as of this phase —
content profile creation through strategy-informed future ideation, with
the loop's autonomous closure (step 22, "future idea generation uses the
updated strategy") demonstrated directly in Phase 8's
`test_strategy_integration.py` and now driven end-to-end without human
intervention for `AUTONOMOUS` profiles in this phase.

## Phase 10 — Scheduler

**Status:** Complete

**Implemented:**
- Closes the gap this file has flagged since Phase 7: `schedule.
  videos_per_day` existed on `ContentProfile` but nothing read it, and
  autonomous mode only ran when the API endpoint was hit by hand.
- `app/services/scheduler.py`: `videos_needed_today()` counts videos
  already produced today per profile (any state — a failed attempt still
  used its slot) against `schedule.videos_per_day`; `profiles_due_for_
  cycle()` returns every non-`MANUAL` profile still under quota.
- `app/workers/scheduler.py`: `check_schedules` (Celery-beat-triggered,
  every 15 minutes — see `celery_app.py`) finds due profiles and
  enqueues one `run_profile_cycle` task per profile, so profiles due at
  the same tick run as independent, parallel Celery tasks rather than
  serially inside one long task. `run_profile_cycle` runs the existing
  `run_autonomous_cycle()` and swallows the two expected/unattended
  outcomes (mode flipped to manual since enqueued; dedup rejected every
  idea this cycle) instead of letting Celery retry into the same result.
- `docker-compose.yml`: new `beat` service, same pattern as `worker`.

**Tests:** 8 new (`test_scheduler.py`): quota counting (zero videos,
today-only counting, never-negative), due-profile selection (skips
`MANUAL`, includes `SEMI_AUTOMATIC`, skips quota-already-met), and
`check_schedules` enqueuing exactly one task per due profile (real
Celery task object, `.delay` mocked — no broker needed to run the suite).
84 passed, 2 skipped (unrelated Gemini live tests) across the whole repo.

**Verified live** against a real Redis broker and a real Celery worker
(not just the test suite, per this project's own standing rule): created
a profile with an unmet quota, called `check_schedules.delay()`, watched
it correctly return `[profile_id]` and the worker log show
`run_profile_cycle` received and executed — it ran the actual
`run_autonomous_cycle()` pipeline for real (failing only on an unrelated,
concurrently-in-progress TTS provider change in `.env`, not on anything
in this phase).

**Known limitations:**
- `"today"` is a fixed UTC day, not the profile's own local time —
  `schedule` has no `timezone` field yet (that belongs with the Phase 6
  publishing scheduler's `posting_windows`, not this one). Add
  `schedule.timezone` and use it in `videos_needed_today` if profiles
  ever need midnight-local resets.
- No `posting_windows` — a due profile's cycle can be enqueued at any
  point in the 15-minute beat tick, not pinned to specific times of day.
- Retries/backoff for `run_profile_cycle` on transient errors (a real
  provider timeout, not the two expected exceptions) rely on Celery's
  defaults — nothing in this phase configures per-task retry policy.

**Next task:** none currently assigned — see the "Genuine gaps" list a
user-driven review of this file surfaced: no `ResearchAgent` (Phase 1),
missing docs (`DATABASE.md`, `AGENTS.md`, `VIDEO_PIPELINE.md`,
`PUBLISHING.md`, `ANALYTICS.md`, `DEPLOYMENT.md`, `API.md`,
`OPERATIONS.md`), and no documented security review pass.

## Phase 5 addendum — Real TTS provider

**Status:** Complete, live-tested

**Implemented:**
- `GeminiTTSProvider` (`app/providers/tts.py`): real narrated speech via
  `gemini-2.5-flash-preview-tts`. Gemini returns raw 16-bit mono PCM
  (`audio/L16;codec=pcm;rate=24000`, parsed from the response's
  `mime_type` rather than hardcoded), wrapped into a proper WAV container
  with the stdlib `wave` module — no new dependency. Selected via
  `TTS_PROVIDER=gemini` + `TTS_API_KEY`.
- **Real narration doesn't land on the storyboard's guessed
  `duration_seconds`** — a real sentence takes however long it takes to
  say, unlike the mock's silence which hits any requested length exactly.
  `produce_video()` now measures each scene's actual generated audio
  duration (`_wav_duration_seconds`, stdlib `wave`) and retimes the scene
  to it before building captions and rendering, so the SRT and the video
  clip stay in sync with what's actually playing instead of drifting from
  an LLM's duration estimate. This applies uniformly to both providers;
  it's a no-op for the mock since silence already matches the request.
- **Live-tested** 2026-08-31: a real call synthesized "No body was ever
  found." in ~3s; confirmed real (non-silent, correctly-shaped mono
  16-bit) audio via `wave` inspection, both as an isolated provider call
  and via `pytest` (`test_gemini_tts.py`, skipped without `GEMINI_API_KEY`).

**A real test-isolation bug, found and fixed the same way as Phase 9's**
(via live use, not just the test suite): once a real `backend/.env` with
`TTS_PROVIDER=gemini` existed for manual testing, the *entire* pytest
suite silently started making real Gemini API calls instead of using
mocks — `pydantic-settings` reads `backend/.env` from the working
directory regardless of whether it's a real run or a test run, and nothing
was overriding that for tests. 17 tests failed from real API errors
(mostly rate-limiting) before the fix. Fixed in `tests/conftest.py`:
force `LLM_PROVIDER`/`IMAGE_PROVIDER`/`TTS_PROVIDER`/`EMBEDDING_PROVIDER`
to `mock` for the whole test session, before any app module import (since
`get_settings()` is `@lru_cache`'d and several modules call it at import
time). The dedicated live-gated tests (`test_gemini_*.py`) are unaffected
— they instantiate their provider directly from `GEMINI_API_KEY`, bypassing
`get_settings()` entirely. This is a real hazard for anyone else who adds
a local `.env` for manual testing on this project; worth knowing about.

**On secret handling this pass:** the API key was, twice, nearly exposed
in this conversation — once by being typed directly in chat instead of
via a private channel, and once by this assistant using `Read` on
`backend/.env` (which printed the key line into the transcript) instead
of editing the non-secret `TTS_PROVIDER` line blindly with `sed`. Both
times the user was told to rotate the key. If you're reading this later:
treat any key that has appeared in this project's chat history as
burned, and never `Read`/`cat` a `.env` file that holds a live secret —
edit it blindly (`sed`, or a targeted regex) when only a non-secret field
needs to change.

**Known limitations:**
- Single fixed voice (`Kore`) — not configurable per content profile yet;
  `profile.style.narration` (e.g. "dramatic") isn't mapped to a voice
  choice. Straightforward to add once it matters.
- No word-level caption timing from TTS — captions are still one cue per
  scene (see Phase 2's `ponytail:` note in `app/video/captions.py`); real
  per-word timestamps would need Gemini TTS's timing metadata (not
  requested/parsed here) or an ASR pass.

**Next task:** none currently assigned. See the "Genuine gaps" list above
this section (still applicable) plus this addendum's known limitations.
