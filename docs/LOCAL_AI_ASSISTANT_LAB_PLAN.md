# Local AI Assistant Lab Plan

Last updated: 2026-06-26

## Status (updated after the RC2 follow-up hardening pass)

The formal Phase 4.0-4.5 lab plan below remains a **docs-only plan** -- no Open WebUI
iframe, no RAG/Knowledge integration, no web search, no vision chat, and no
Story-Studio-aware assistant tools exist inside AI Story Studio. That part of this
document is unchanged in substance from the RC2 milestone pass.

**One narrow exception**, added in the same-day RC2 follow-up hardening pass (separate
from this lab plan, not an implementation of it): `POST /api/projects/{id}/assistant/ask`
-- a single-turn, stateless question about one project's own data, answered directly by
the existing Ollama model (`qwen2.5:7b`). No RAG, no conversation memory, no citations,
no web search. This is the "المساعد المحلي" Tier 1 minimal feature in the Studio UI, not
a replacement for this lab's plan. **Open WebUI remains the real path to a full
ChatGPT-like local assistant** (RAG, web search, vision, conversation history) -- see
`docs/PRODUCTION_STUDIO_FINAL_REPORT.md` Milestone 13 and `docs/API_CONTRACTS.md` for
the endpoint contract. Story Studio assistant tools (Phase 4.5) remain the last step,
only after the earlier lab phases pass their own benchmarks.

## Purpose

Document a realistic future path for a local/internal AI assistant that feels similar to ChatGPT or Gemini from a user perspective, but uses the existing AI Server stack first.

This is a future lab track. It is not part of Phase 1.5.

## Existing Infrastructure

We are not starting from scratch. The AI Server already has:

- Open WebUI running as a chat interface.
- Ollama running as the local model runtime.
- Docker environment for AI services.
- AI Story Studio as a separate backend/frontend product.
- Project docs, API contracts, prompts, and roadmap files that are suitable for RAG/Knowledge testing.

Use placeholders in docs and configuration examples:

- `AI_SERVER_LAN_IP`
- `OPEN_WEBUI_PORT`
- `OLLAMA_PORT`

Do not write real IPs or credentials in docs.

## Why Not Build From Scratch

Building a custom ChatGPT/Gemini clone now would duplicate features Open WebUI already provides:

- Chat UI.
- Model selection.
- Conversation history.
- File/image uploads.
- Knowledge/RAG.
- Web search.
- Tools/functions/pipelines.
- User/workspace organization.

The realistic plan is to benchmark and configure Open WebUI first. AI Story Studio should only integrate assistant features later if the lab proves useful and safe.

## Phase 4.x Roadmap

### Phase 4.0 — Local AI Assistant Lab Research

Scope:

- Review Open WebUI capabilities.
- Review Ollama model list and model management.
- Define practical use cases for Hamza and AI Story Studio.
- Compare Open WebUI with alternatives such as AnythingLLM, LibreChat, and Dify as patterns only.
- No integration inside AI Story Studio.

Exit criteria:

- Clear recommendation: use Open WebUI as-is, extend it, or later create a small Story Studio assistant bridge.

### Phase 4.1 — Model Benchmark for Chat

Scope:

- Benchmark Arabic chat.
- Benchmark English chat.
- Benchmark coding/reasoning.
- Benchmark speed and context length.
- Benchmark only models available in Ollama or explicitly approved for pull later.

Candidate text/chat models:

- `qwen2.5:7b` current/default candidate.
- `llama3.1` or `llama3.2` 8B if available/suitable.
- `gemma` or `mistral` if already available.
- Any model actually shown by `ollama list`.

Exit criteria:

- Default model candidates selected by task type.
- Limits documented: Arabic, English, reasoning, coding, long context.

### Phase 4.2 — Knowledge / RAG Setup

Scope:

- Upload project docs, roadmap, API contracts, prompts, and selected project files.
- Test source-bound answers.
- Test citations.
- Test whether the assistant says “I do not know” when evidence is missing.
- Tune chunking/context settings.

Candidate embedding models:

- `nomic-embed-text`.
- `mxbai-embed-large`.
- Any embedding model compatible with Open WebUI/Ollama and suitable for hardware.

Exit criteria:

- Project-doc Q&A works with citations.
- RAG answer quality is better than pure model memory.
- Hallucination eval questions have documented results.

### Phase 4.3 — Web Search

Scope:

- Test Open WebUI web search.
- Document a provider later, such as SearXNG or another safe provider.
- Require sources/citations.
- Use web search for current external information, not as the main source of project truth.

Exit criteria:

- Search results are useful and cited.
- Latency and failure modes are documented.
- The assistant does not invent sources.

### Phase 4.4 — Vision Chat

Scope:

- Benchmark vision candidates on uploaded images/screenshots.
- Test UI screenshot analysis.
- Test image description and scene-quality review.
- Test Arabic and English prompts.

Candidate vision models:

- `qwen2.5vl:7b` or a hardware-suitable size.
- `llama3.2-vision` if suitable.
- `llava` as a lighter fallback.

Exit criteria:

- A vision model is marked PASS/CANDIDATE/BLOCKED.
- Speed, VRAM, and accuracy are documented.
- Human review remains required.

### Phase 4.5 — Story Studio Assistant Tools

Scope:

- Assistant reads current story/project context through backend-approved data.
- Assistant suggests story improvements.
- Assistant reviews `scenes.json`.
- Assistant checks continuity.
- Assistant suggests image prompts.
- Assistant suggests character/location/story bibles.
- Assistant flags possible errors.

Rules:

- The assistant does not automatically modify project data.
- User approval is required before applying changes.
- No direct browser-to-AI-Server integration.
- Do not mix Open WebUI storage with Story Studio project storage without a plan.

## Open WebUI Role

Open WebUI remains the lab interface for now:

- Chat.
- Model selection.
- Conversation history.
- File/image upload.
- Knowledge/RAG testing.
- Web search testing.
- Vision model testing.

No iframe, no direct app integration, and no custom clone in the current phase.

## Ollama Role

Ollama remains the local model runtime:

- Text/chat models.
- Vision models if installed.
- Embedding models if used by Open WebUI.

No model is accepted without benchmark on the AI Server.

## RAG Strategy

Fine-tuning is not the first plan.

Start with:

- Project docs as Knowledge/RAG.
- Strict system prompts.
- Source-bound mode.
- Citations.
- “I do not know” when evidence is missing.
- Eval questions to test hallucination.
- Context length tuning for Ollama models.

Fine-tuning is deferred until RAG + prompts + model selection prove insufficient.

## Web Search Strategy

Use web search only when needed for current external information.

Rules:

- Require citations.
- Do not trust unsourced answers.
- Do not use web search as the main source for internal project state.
- Benchmark the provider before relying on it.

## Vision Model Strategy

Vision chat is useful for:

- UI screenshots.
- Generated image review.
- Scene image critique.
- Uploaded reference image understanding.

But it requires benchmark because local vision models can be slow, inaccurate, or limited by VRAM.

## Anti-Hallucination Strategy

Use layered controls:

1. RAG/Knowledge from project files.
2. Strict system prompts.
3. Citations/source-bound answers.
4. Refuse to answer when evidence is missing.
5. Web search only when explicitly useful.
6. Confidence/limitations in answers.
7. Eval questions for recurring checks.

Do not rely on “training” as the first solution.

## Benchmark Gates

Every assistant capability needs a small benchmark:

- Chat model quality.
- Arabic response quality.
- Coding/reasoning quality.
- RAG groundedness.
- Web search citation quality.
- Vision model image understanding.
- Latency on AI Server.
- VRAM impact.

Verdicts should use the same style as the media benchmark gate:

- `PASS`
- `CANDIDATE`
- `BLOCKED`
- `REJECTED`

## Security Boundaries

- Open WebUI stays a separate service for now.
- No direct browser-to-internal-service integration inside AI Story Studio.
- No iframe integration now.
- No secret/IP in docs.
- Any future AI Story Studio assistant integration must go through backend-approved APIs.
- Do not mix Open WebUI storage and Story Studio project storage without a migration/sync plan.

## Practical Use Cases

Useful future lab tasks:

- Ask questions about project docs.
- Review roadmap and API contracts.
- Review error logs.
- Upload a UI screenshot and ask for feedback.
- Upload `scenes.json` and request a review.
- Upload a long story and request analysis.
- Choose an Ollama model based on the task.
- Use Open WebUI as a general assistant while AI Story Studio stays the production app.

## Not Now / Future Only

Not now:

- No new chat UI.
- No Open WebUI integration in AI Story Studio.
- No iframe.
- No Docker/service changes.
- No model downloads.
- No fine-tuning.
- No automatic project edits by assistant.

Future only:

- Assistant tools inside Story Studio.
- Project-aware assistant suggestions.
- Vision-assisted UI/image review.
- Web-search-assisted research.
- Optional backend bridge after benchmark.

## Research References

- Open WebUI features: https://docs.openwebui.com/features/
- Open WebUI RAG: https://docs.openwebui.com/features/chat-conversations/rag/
- Open WebUI web search: https://docs.openwebui.com/category/web-search/
- Open WebUI model workspace: https://docs.openwebui.com/features/workspace/models/
- Open WebUI pipelines: https://github.com/open-webui/pipelines
- AnythingLLM document/RAG patterns: https://docs.anythingllm.com/chatting-with-documents/introduction
- Qwen2.5-VL on Ollama: https://ollama.com/library/qwen2.5vl
- Llama 3.2 Vision on Ollama: https://ollama.com/library/llama3.2-vision

