# AI Story Studio — Production Studio RC2 Report

Date: 2026-06-26

## 1. Verdict

**READY** for Hamza's manual QA pass. All milestones (0, A through J) from the
Production Studio RC2 execution plan are implemented, tested with real and synthetic
data, committed, and pushed to `origin/main`. No known broken paths in the existing
Production MVP.

## 2. Critical Long Story Fix

Root cause: `OllamaProvider.generate_text()` caught every `requests.RequestException`
(including `Timeout`) with one generic Arabic message ("تعذر الاتصال بخدمة Ollama"),
so a long story (~13k+ characters) that timed out on a single oversized prompt was
misreported as a connection failure even when Ollama was healthy.

Fix: `Timeout`, `ConnectionError`, and `HTTPError` are now caught separately with
distinct Arabic messages (timeout → suggests long-story mode; connection error → the
original message; HTTP error → status-aware, with a context-overflow hint if the
response body suggests it). Stories longer than `LONG_STORY_CHUNK_CHARS` (default
6000, configurable via `.env`) are split into ordered paragraph/sentence-bounded
chunks and improved sequentially, then joined — no merge/smoothing pass afterwards
(that would just reintroduce one long prompt over the whole result).

Verified: mocked-exception injection confirmed `ReadTimeout`/`ConnectTimeout` produce
the timeout message and `ConnectionError` still produces the original message. A real
synthetic 7828-character story split into 2 chunks and succeeded; a real 5798-character
story stayed at 1 chunk. Both confirmed via `scripts/test_long_story_improve.py`.

## 3. Milestones Completed

| Milestone | Status | Commit |
|---|---|---|
| 0 — Long story improve fix | DONE | `3686109` (prior session) |
| A — Lightweight job progress foundation | DONE | `e265858` (prior session) |
| B — Project Timeline View | DONE | `28b1e72` |
| C — Project Asset Library | DONE | `28b1e72` |
| D — Quality Review Board | DONE | `77d616a` (schema), `28b1e72` (UI) |
| E — Ken Burns / Better Video Assembly | DONE | `77d616a` |
| F — Prompt / Story Bible Editor Polish | DONE | `f1ce77a` (prompt-preview endpoint), `28b1e72` (UI) |
| G — Simple Image Studio | DONE | `f1ce77a` (endpoint), `28b1e72` (UI) |
| H — Safety & Rights Checklist | DONE | `77d616a` (schema), `28b1e72` (UI) |
| I — Model / Engine Dashboard | DONE | `c1824ae` |
| J — Local Assistant Lab docs | DONE | `63c7554` |
| Final RC2 docs | DONE | this commit |

Note on commit granularity: `backend/app/schemas.py` picked up fields for D, E, and H
in one continuous edit pass, and `frontend/src/App.tsx`/`styles.css` carry UI for every
milestone B-I. Splitting either into separate per-milestone commits would have required
risky line-by-line `git add -p` staging across non-contiguous regions of large files,
so five commits were made instead of nine — grouped by what could be cleanly isolated.
Full disclosure in `docs/DECISION_LOG.md`'s 2026-06-26 entry.

## 4. User Workflow Now

Story (with chunked long-story improve) → split into editable scenes → audio (sync or
job-based, live progress) → images (sync or job-based, live progress; optional prompt
preview before generating) → video (static or Ken Burns + optional fade, sync or
job-based) → subtitles (auto, always in sync with the rendered video) → **Timeline**
(see every scene's status in one place) → **Asset Library** (browse/download every
file without opening the ZIP) → **Quality Review Board** (approve/flag/reject each
scene with notes) → **Simple Image Studio** (separate single-prompt image generation,
not tied to the story) → Export ZIP. The safety/rights checklist and engine-status
dashboard are available throughout, not gated behind a specific step.

## 5. Job/Progress System

Endpoints: `GET /api/jobs/{job_id}`, `GET /api/projects/{project_id}/jobs`,
`POST /api/projects/{id}/story/improve/jobs`, `.../images/generate-all/jobs`,
`.../video/render/jobs`, `.../tts/generate-all/jobs`.

UI behavior: each long-running action now polls its job every 1.2s and shows
`message_ar` live (e.g. "جاري توليد صورة المشهد 3 من 6..."). No fake percentage/ETA —
deliberately, per the no-fake-progress rule. Original synchronous endpoints are
unchanged and still used for short stories (instant feedback, no polling overhead).

Known limits (disclosed, not hidden): in-process only (a backend restart mid-job leaves
the job stuck on `running` with no recovery sweep); no cancel endpoint; no dedicated
retry endpoint (clicking the action again just starts a fresh job, which works but
isn't a purpose-built retry UX).

## 6. Timeline / Asset Library / Review Board

- **Timeline** ("الخط الزمني"): one row per scene — duration, narration preview,
  audio/image/subtitle status, whether the scene was included in the last video
  render (and why if skipped), review status, validation warnings, and quick
  jump/play/preview actions. Entirely derived from already-fetched project/audio/
  image/video state; no new backend endpoint needed.
- **Asset Library** ("مكتبة الأصول"): every project file (original/improved story
  text, scenes.json, per-scene audio, final_story.wav, per-scene images, video,
  SRT/VTT, export.zip) grouped with available/missing state and backend-proxied
  download links only — no filesystem paths, no AI Server URLs.
- **Quality Review Board** ("مراجعة الجودة"): `Scene.review_status`
  (pending/approved/needs_retry/rejected) + `review_notes`, persisted via the existing
  `PUT /api/projects/{id}` (no new endpoint). A non-blocking warning appears on the
  Export step when scenes are unreviewed. Verified via a real save/reload round-trip:
  setting `review_status="approved"` and `review_notes="looks good"` on a throwaway
  project, then reloading it, returned the same values.

## 7. Video Improvements

`static` (default, unchanged behavior) vs `ken_burns` (ffmpeg `zoompan`, slow zoom-in
capped at 1.15x) vs `transition: fade` (per-segment fade-in/fade-out, not a true
crossfade between segments — the concat step still uses lossless `-c copy`, disclosed
as a deliberate low-risk simplification rather than re-encoding the whole timeline).

Duration sync evidence (`scripts/test_ken_burns_video.py`, synthetic 6-scene project,
`ken_burns` + `fade`, 2.0s real audio per scene): rendered `duration_seconds` = 12,
expected total = 12.0s (within the 1.5s tolerance), all 6 scenes included, subtitle
file has exactly 6 cues. The Milestone 0 audio-duration-sync guarantee holds for every
video mode, not just `static`, because both paths share the same
`ProjectStorage.get_scene_render_durations()` source of truth.

## 8. Image Studio

Done. `POST /api/images/standalone/jobs` — one prompt, one image, no scene/project
attachment, no continuity-bible mixing. Verified end-to-end with one real small
(256×256) ComfyUI job: job created, polled to `done`, file downloadable. Polling/
download reuse the already-existing project-agnostic `GET /api/images/jobs/{job_id}`
and `.../download` endpoints.

## 9. Validation Results

| Check | Result |
|---|---|
| `python scripts/check_utf8.py` | PASS |
| `python -m compileall backend/app` | PASS |
| `docker compose config` | PASS |
| `docker compose exec -T frontend npm run build` | PASS (tsc + vite, no errors) |
| `python scripts/smoke_phase0_workspace.py` | PASS (9/9) |
| `python scripts/final_acceptance_check.py` | PASS (27/27) |
| `python scripts/test_video_audio_duration_sync.py` | PASS (8/9, 1 graceful skip — no host ffprobe) |
| `python scripts/test_ken_burns_video.py` (new) | PASS (11/11, 1 graceful skip) |
| `python scripts/test_job_system.py` | PASS (all) |
| `python scripts/test_long_story_improve.py` | PASS (real Ollama) |
| Direct verification: `/api/system/status` | PASS — real Ollama/TTS/image health + ffmpeg availability returned, no URLs |
| Direct verification: schema fields round-trip (`video_mode`, `safety_*`) | PASS |
| Direct verification: review status/notes persist after reload | PASS |
| Direct verification: prompt-preview endpoint | PASS — returns assembled prompt + negative prompt without spending a job |
| Direct verification: standalone image studio | PASS — one real ComfyUI job completed end-to-end |

## 10. Git / Media Safety

- Branch: `main`
- Latest commit: `28b1e72` (frontend UI), preceded by `63c7554`, `c1824ae`, `f1ce77a`, `77d616a` — all pushed to `origin/main`
- Push status: confirmed `main` in sync with `origin/main` after each commit
- Working tree: clean before this report's docs commit
- No `.env`, generated media (`png/wav/mp3/mp4/zip`), or model files (`safetensors/ckpt/gguf`) staged in any commit — verified via `git status --short` before every commit
- `data/jobs/` added to `.gitignore` (new in this RC2 pass, alongside the existing `data/projects/` exclusions)

## 11. Remaining Limitations

Be explicit, not hidden:

- **Image quality remains `CANDIDATE`**, not a final product-quality sign-off (unchanged from MVP).
- **Continuity remains prompt-only (Tier 1)** — the new prompt-preview endpoint shows what's sent, it does not add real cross-scene memory. Real continuity needs a reference workflow (IPAdapter/ControlNet), not started.
- **No AI motion yet** — Ken Burns is an ffmpeg zoom/fade effect, explicitly not Veo/Runway/WanGP-style generated motion.
- **Job system is local-only** — no Redis/Celery/DB, no crash recovery, no cancel endpoint. Fine for one local user, not for concurrent/multi-user use.
- **Fade transition is per-segment, not a true crossfade** between two different scenes' clips (disclosed in section 7 above).
- **No public deployment, no auth** — unchanged, not in scope.
- **Local assistant lab remains docs/plan-only** (`docs/LOCAL_AI_ASSISTANT_LAB_PLAN.md`) — no chat UI, no Open WebUI integration, intentionally.
- **`App.tsx` is now larger** (10 Studio Workflow steps) — splitting it into per-step components remains deferred for the same reason as before (shared state, no live browser this session to verify a large refactor visually), now a slightly higher-value future cleanup.

## 12. Hamza Manual QA Script

1. افتح أي مشروع موجود أو ابدأ مشروعاً جديداً بقصة طويلة (أكثر من 6000 حرف) واضغط "تحسين القصة" — راقب أنها تنجح على أجزاء.
2. اضغط "توليد صور كل المشاهد" ثم "تجميع فيديو القصة" وراقب رسائل التقدم المتغيرة لحظياً.
3. افتح "الخط الزمني" وتأكد أن حالة كل مشهد (صوت/صورة/ترجمة/فيديو/مراجعة) صحيحة.
4. افتح "مكتبة الأصول" وجرّب تحميل كل نوع ملف متاح.
5. افتح "مراجعة الجودة"، اعتمد مشهداً، ضع ملاحظة على آخر، أعد تحميل المشروع وتأكد من بقاء الحالة.
6. في خطوة الفيديو، جرّب "حركة خفيفة" + "تلاشي خفيف"، احفظ، وأعد تجميع الفيديو — قارن النتيجة بالوضع الثابت.
7. افتح "استوديو الصور المستقل" وولّد صورة من وصف واحد بدون أي مشروع.
8. في خطوة الصور، جرّب "معاينة prompt المشهد الأول" وتأكد أنها لا تستهلك أي توليد فعلي.
9. افتح لوحة "حالة الخدمات" تحت العنوان الرئيسي واضغط "فحص حالة الخدمات".
10. حمّل ZIP النهائي وتأكد أن كل شيء سابق يعمل كما كان (لا كسر في الـ Production MVP الأساسي).
