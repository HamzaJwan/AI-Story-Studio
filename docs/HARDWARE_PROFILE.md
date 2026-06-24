# Hardware Profile

هذا الملف يوثّق العتاد الحقيقي المتاح للمشروع، لاستخدامه كأساس لأي قرار benchmark لاحقاً (TTS/Images/Video) — حسب `docs/BENCHMARK_PROTOCOL.md`.

لا تضع هنا passwords، tokens، أو أي IP حقيقي خارج ما هو موجود فعلاً في وثائق المشروع الحالية (`AI_SERVER_PROFILE.md`).

---

## Local Dev Machine (Windows)

تم جمعها مباشرة من الجهاز بتاريخ 2026-06-24 عبر أوامر محلية فقط (`wmic`, `docker --version`):

| الحقل | القيمة |
| --- | --- |
| OS | Windows, build 10.0.22631.2861 (Windows 11) |
| CPU | 13th Gen Intel Core i7-13700H — 14 cores / 20 logical processors |
| RAM | ~31.8 GB (34,124,349,440 bytes) |
| GPU | NVIDIA GeForce RTX 3060 (laptop) |
| Disk C: | 263.3 GB free / 582.5 GB total |
| Disk D: | 160.4 GB free / 549.8 GB total |
| Disk E: | 715.6 GB free / 915.8 GB total |
| Docker Engine | 29.4.3 |
| Docker Compose | v5.1.4 |
| Docker Desktop resource allocation | 20 CPUs, ~15.5 GB RAM |

**ملاحظة:** هذا الجهاز يشغّل التطبيق الأساسي (frontend/backend) فقط عبر `docker compose`. هذا الجهاز **ليس** الهدف لأي GPU workload ثقيل (TTS/Image/Video) — تلك تذهب إلى AI Server.

---

## AI Server (waha — IP في `.env` المحلي فقط، راجع `docs/AI_SERVER_PROFILE.md`)

البيانات أدناه موثّقة مسبقاً في `docs/AI_SERVER_PROFILE.md` من تجربة فعلية سابقة على نفس السيرفر (وليست افتراضاً من الذاكرة):

| الحقل | القيمة |
| --- | --- |
| Hostname | waha |
| OS | Ubuntu Server 24.04.4 LTS, kernel 6.8.0-110-generic |
| CPU | 2 × Intel Xeon E5-2699 v4 |
| RAM | 128 GB |
| Target AI GPU | NVIDIA GeForce RTX 4060 Ti |
| Secondary GPU | NVIDIA GeForce GT 710 |
| NVIDIA driver | 580.126.09 |
| CUDA (driver-reported) | 13.0 |
| Docker Engine | 29.4.1 |
| Docker Compose | v5.1.3 |
| Buildx | v0.33.0 |
| Storage driver | overlayfs |
| cgroup driver | systemd |

### ✅ Verified 2026-06-24 (عبر SSH alias `ai-story-server`, بدون password)

| الحقل | القيمة |
| --- | --- |
| VRAM الفعلية | **8,188 MiB (~8GB variant)** — مؤكَّد عبر `nvidia-smi` |
| Docker Engine (محدَّث) | 29.6.0 |
| Docker Compose (محدَّث) | v5.2.0 |
| مساحة القرص | 1.9 TB إجمالي، 116GB مستخدم، **1.7TB متاح** — لا قيد حالياً |
| الشبكة الخارجية (HuggingFace/PyPI) | **متقطعة/غير مستقرة في جلسة 2026-06-24 المسائية** — راجع `docs/DECISION_LOG.md` لتفاصيل تجمّد تحميل SILMA وتذبذب سرعة pip/HF بين ~200 B/s و~530 KB/s لنفس المسار. هذا تذبذب لحظي وليس قيداً دائماً — أعد الفحص عند أي عملية تحميل كبيرة قادمة. |
| خدمات Docker العاملة فعلياً | `tts-worker` (الجديدة، 8851)، `alltalk_tts-main-alltalk-tts-1` (image `erew123/alltalk_tts:cuda`, **يعمل فعلياً** على 7851 — لم يُلمس، read-only فقط)، `openwebui` (3000)، `ollama` (11434)، `portainer` (9000/9443)، `netdata` |

**ملاحظة مهمة:** يوجد AllTalk حاوية فعلية شغّالة بالفعل على AI Server (`erew123/alltalk_tts:cuda`, port 7851) — لم تُختبر بعد كـ Benchmark Gate حقيقي، لكنها موجودة وجاهزة للفحص لاحقاً (تُحدِّث حالتها في `docs/TTS_ENGINE_BENCHMARK_MATRIX.md` من `CANDIDATE` فقط بعد اختبار فعلي بنفس منطق Phase 1.2).

### أمر التحديث المستخدَم (مرجع — read-only فقط)

```bash
ssh ai-story-server "nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader"
ssh ai-story-server "df -h /"
ssh ai-story-server "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'"
```

لم يُستخدم أي password — SSH key-based فقط عبر alias `ai-story-server` المُعرَّف محلياً.

---

## القيود المهمة (Constraints)

- App Server (هذا الجهاز) لا يشغّل GPU workloads مباشرة — راجع `docs/AI_SERVER_SERVICES_ARCHITECTURE.md`.
- أي TTS/Image/Video engine يجب أن يُختبر على AI Server (وليس على Local Dev Machine) لأن هذا هو العتاد المستهدف فعلياً للتشغيل.
- لا نفترض VRAM/driver/CUDA من الذاكرة لأي قرار — فقط من `nvidia-smi` فعلي حديث.
- لا يجوز تشغيل `docker prune`، إيقاف containers، أو لمس Ollama/Open WebUI/Portainer/Netdata على AI Server إلا بإذن صريح من حمزة لكل عملية.
