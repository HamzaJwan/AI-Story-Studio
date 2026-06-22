# AI Server Profile

## Purpose

خادم محلي داخل LAN لتشغيل Ollama/Open WebUI وخدمات AI المستقبلية.

## Hardware

* Platform: Bare-metal server
* CPU: 2 x Intel Xeon E5-2699 v4
* RAM: 128 GB
* Target AI GPU: NVIDIA GeForce RTX 4060 Ti
* Secondary GPU: NVIDIA GeForce GT 710

## OS

* Ubuntu Server 24.04.4 LTS
* Hostname: waha
* Kernel: 6.8.0-110-generic

## NVIDIA / CUDA

* NVIDIA driver: 580.126.09
* nvidia-smi: working
* CUDA reported by driver: 13.0

## Docker

* Docker Engine: 29.4.1
* Docker Compose: v5.1.3
* Buildx: v0.33.0
* Storage driver: overlayfs
* cgroup driver: systemd
* Service: active/enabled

## Ollama

* Status: Running and reachable on LAN
* Base URL: set in local `.env` only
* Do not store real IP in Git

## Available Models

* qwen2.5:7b — recommended default for Phase 0 story splitting and JSON
* llama3.1:8b — fallback for story tasks
* qwen2.5-coder:7b — coding only, not default for story
* qwen2.5-coder:1.5b-base — lightweight coding only
* llama3.2-vision:latest — future vision tasks
* llava:latest — future vision tasks
* nomic-embed-text:latest — future embeddings/search

## Phase 0 Recommendation

* Use `qwen2.5:7b` as default `OLLAMA_MODEL`.
* Use `llama3.1:8b` as fallback.
* Do not use coder or vision models for story narration/splitting.
* Do not pull new models until Phase 0.1 works.

## Security Rules

* Do not document SSH username/password.
* Do not document root credentials.
* Do not hardcode the server IP in code or docs.
* Use `.env` locally for `OLLAMA_BASE_URL`.
* Do not expose Ollama publicly.
* Production deployment requires Auth and network restrictions.

## Local .env Example

Use placeholders only:

```env
OLLAMA_BASE_URL=http://AI_SERVER_LAN_IP:11434
OLLAMA_MODEL=qwen2.5:7b
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## Notes

* This server is suitable for Ollama Phase 0.
* Future TTS/image/video workloads should be benchmarked before integration.
