# Image Continuity Strategy

Last updated: 2026-06-25

## Problem

Scene-by-scene image generation can easily break story continuity:

- A character changes face, age, clothing, or body type.
- A white door becomes green in the next scene.
- The same room changes layout.
- Important props disappear.
- Long stories drift in style after 10+ scenes.

Prompt-only generation is not enough for reliable continuity.

## Manual ComfyUI Lesson

Hamza's manual ComfyUI test confirmed this risk in practice. A prompt that tried to reuse the
"same old Libyan storyteller" still drifted into a different character, including a gender change
in one result. This means the product must not rely on `same character` wording alone.

For MVP scene-image prompts, repeat the core identity in every prompt:

- Gender lock: male/female must be explicit when important.
- Age lock: old man / elderly woman / child, etc.
- Role and cultural identity: e.g. elderly Libyan male storyteller.
- Fixed clothing and props: robe, wrapped headscarf, lantern, wooden window.
- Negative prompt: explicitly block unwanted gender, age, style, and artifact drift.

Details are recorded in `docs/COMFYUI_MANUAL_TEST_NOTES.md`.

## Strategy

### 1. Story Bible

Create a visual bible before image generation:

- Story era and location.
- Visual style and color palette.
- Camera language.
- Lighting mood.
- Forbidden style changes.

### Story / Style Bible Editor — Future UI

Later, the app should provide an editor for:

- Story Bible.
- Character Bible.
- Location Bible.
- Object Bible.
- Visual Style Bible.
- Forbidden changes.

Examples:

- Character is a 40-year-old man and must not switch gender.
- The white door must remain white.
- Clothing, hair, room layout, and atmosphere should stay consistent.
- Same character should remain recognizable across 10+ scenes.
- Style can be cinematic, anime, cartoon, realistic, military documentary, horror, warm storybook, or marketing.

This belongs to Phase 2.3 / Phase 2.4, not Phase 1.5.

### 2. Character Bible

For each recurring character:

- Name and role.
- Face/age/body/clothing details.
- Persistent accessories.
- Emotional range.
- Negative constraints: what must not change.
- Optional reference image once the product supports safe references.

Minimum MVP character fields:

- `gender`
- `age_range`
- `role`
- `visual_identity`
- `clothing`
- `persistent_props`
- `must_not_change`

### 3. Location Bible

For every recurring place:

- Layout.
- Fixed objects and colors.
- Doors/windows/furniture/landmarks.
- Time of day rules.
- “Must stay the same” notes.

Example: if the story defines a white door, the prompt and continuity metadata should explicitly keep that door white in every relevant scene.

### 4. Object Bible

Track important objects:

- Color, material, size.
- Owner or location.
- Symbolic meaning.
- Scenes where the object appears.

### 5. Reference Tiers

Use the lightest reliable method first:

| Tier | Method | Use |
|---|---|---|
| 1 | Prompt-only + style preset | Fast draft, weak continuity |
| 2 | Fixed style + seed strategy | Better consistency, still limited |
| 3 | Image reference / IP-Adapter-style workflow | Character/style continuity |
| 4 | ControlNet-style layout/pose/depth guides | Pose, structure, composition |
| 5 | Character LoRA/InstantID/reference pack | Stronger recurring character continuity, benchmark first |

## Long Stories

For stories longer than 10 scenes:

- Generate in batches of 3–6 scenes.
- Review each batch before continuing.
- Reuse character/location anchors in every batch.
- Refresh prompts from the story bible, not only from the previous scene.
- Retry failed or inconsistent scenes individually.
- Record seed/model/workflow metadata per scene.

## Hardware Constraints

The AI Server has enough GPU for SDXL-class generation, but 8GB VRAM is tight. Avoid stacking multiple heavy ControlNet/IPAdapter-style workflows until benchmarked. Prefer staged benchmarks:

1. Base SDXL.
2. SDXL with style preset.
3. SDXL with one reference mechanism.
4. SDXL with continuity references across 6 scenes.

## Useful References

- IP-Adapter paper: https://arxiv.org/abs/2308.06721
- IP-Adapter repository: https://github.com/tencent-ailab/IP-Adapter
- ControlNet paper: https://arxiv.org/abs/2302.05543
- ComfyUI startup flags / VRAM options: https://docs.comfy.org/development/comfyui-server/startup-flags
- ComfyUI ControlNet + IPAdapter style workflow: https://comfyui.org/en/image-style-transfer-controlnet-ipadapter-workflow
- RunComfy consistent character workflow examples: https://www.runcomfy.com/comfyui-workflows/create-consistent-characters-within-comfyui
