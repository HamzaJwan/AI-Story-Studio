# Manual QA Checklist — AI Story Studio Production MVP

Last updated: 2026-06-25

This checklist is for Hamza to manually try the full Studio MVP pipeline in the browser. Every item below was already verified by the executor with real backend requests and real generated files (see `docs/DECISION_LOG.md` for evidence per phase) — this pass is about product feel and judgment calls, not technical correctness.

Open the app at `http://localhost:5173` before starting (or your configured `FRONTEND_PORT`). The page top has a **"Studio Workflow"** step bar (القصة، المشاهد، الصوت، الصور، الفيديو والترجمة، التصدير) — click a step to jump to its panel; each section below corresponds to one step. Each step shows a ✓ once it has data (scenes/audio/images/video), and the project title shows **"محفوظ"** or **"تغييرات غير محفوظة"** so you always know whether your last edit was saved.

## 1. Story → Scenes

- [ ] Type or paste a story in "النص الأصلي", pick a tone, click "تحسين القصة" — improved text appears.
- [ ] Click "تقسيم إلى مشاهد" — scene cards appear with Arabic narration + English image prompts.
- [ ] Edit a scene's title/narration/duration — changes stick after "حفظ المشروع".
- [ ] Reload the project from the sidebar list — edits persisted.

## 2. Audio Studio

- [ ] Click "فحص خدمة الصوت" — shows connected (or a clear "غير مفعّلة" if `TTS_SERVICE_URL` isn't set).
- [ ] Generate audio for one scene — hear it play in the browser, no ZIP needed.
- [ ] Generate audio for all scenes — each scene shows a playable/downloadable result.
- [ ] Play/download the full-story audio (`final_story.wav`).

## 3. Image Studio

- [ ] Click "فحص خدمة الصور" — shows connected (or a clear message if not configured).
- [ ] Read the quality note in the panel — it should say image quality is experimental/`CANDIDATE`, not a final guarantee. **This is the core product judgment call: does the image quality meet your bar for real use?**
- [ ] Generate an image for one scene — preview appears, download works.
- [ ] Generate images for all scenes — see which succeeded/failed.
- [ ] Regenerate one scene's image — it overwrites, new image looks different (random seed each time).

## 4. Continuity Controls

- [ ] Fill in "الشخصيات الثابتة" with a short character description (e.g., an elderly man, grey beard, brown coat).
- [ ] Fill in "أسلوب القصة العام" with a lighting/mood note.
- [ ] Save the project, then regenerate a scene's image.
- [ ] **Judgment call:** does the new image visibly reflect the character/style description? Compare it to a scene generated before you filled in the bibles.
- [ ] Try a different "النمط البصري" preset (e.g., switch from cinematic to warm storybook) and regenerate — does the visual style actually change?

## 5. Video Assembly

- [ ] With at least one scene having a saved image (audio optional), click "تجميع فيديو القصة".
- [ ] Wait for the status message — it reports which scenes were included and which were skipped (and why).
- [ ] Play the video preview in the browser; download it and play it in a normal video player too.
- [ ] **Judgment call:** is a static-image-per-scene video (no motion, no AI video, hard cuts only) an acceptable MVP deliverable, or does it need Phase 3.1 polish (transitions, title cards) before sharing with anyone?

## 6. Subtitles

- [ ] Download `.srt` and open it in a text editor or video player — Arabic text reads correctly (no broken characters), one subtitle block per scene.
- [ ] Download `.vtt` and check it has the `WEBVTT` header and the same Arabic text.
- [ ] If you played the rendered video, try loading the `.srt`/`.vtt` as an external subtitle track in a video player (e.g., VLC) and confirm timing roughly lines up with the narration.

## 7. Full Export

- [ ] Click "تحميل حزمة المشروع ZIP" and open it.
- [ ] Confirm it contains: `story.txt`, `improved_story.txt`, `scenes.json`, `metadata.json`, `subtitles/story.srt`, `subtitles/story.vtt`, `audio/` (per-scene + `final_story.wav` if generated), `images/` (per-scene PNGs if generated), `video/final_story.mp4` (if rendered).
- [ ] Check `metadata.json` inside the ZIP — it should honestly report counts and known limitations (it will say image quality is `CANDIDATE` and continuity is prompt-only, not pixel-level).

## 8. Security Sanity Check (optional, for your own peace of mind)

- [ ] Open browser dev tools → Network tab while generating audio/images/video.
- [ ] Confirm every request goes to your local backend (`localhost:8810` or your configured port) — **never** directly to the AI Server's address. The backend is the only thing that talks to AI Server services.

## Outcome

After going through this list, the main product decisions are:
1. Is image quality (Phase 2.0–2.3) good enough to use for real, or does it need a different engine/workflow before relying on it?
2. Is the basic ffmpeg video assembly (Phase 3.0) an acceptable "first cut" video, or is Phase 3.1 polish (transitions, subtitle burn-in) needed before it's shareable?
3. Which roadmap track should come next — Phase 2.7 (Project Timeline/Asset Library/Quality Review Board), Phase 3.1 (video polish), or Phase 4.x (local assistant lab)?

None of these are technical blockers — the pipeline works end-to-end with real data. They are product calls that only Hamza can make.
