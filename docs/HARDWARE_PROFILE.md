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

### ⚠️ Pending Verification (غير مؤكد بدقة بعد)

الحقول التالية **غير موجودة** بدقة في أي وثيقة سابقة ويجب تأكيدها بأمر حقيقي قبل أي benchmark جديد، لأن القرار لا يُبنى على افتراض:

- **VRAM الفعلية بالـ GB** لكرت RTX 4060 Ti المثبت فعلياً (الكرت متوفر بنسختين 8GB و16GB — لا نفترض أيهما).
- **مساحة القرص الفعلية المتاحة** (`df -h`) على السيرفر الآن.
- **القيود الحالية على الشبكة** (LAN bandwidth, latency من جهاز التطوير إلى السيرفر).
- **الخدمات الحالية الفعلية تحت Docker** (`docker ps`) لحظة كتابة هذا الملف — حتى لا نتعارض مع Ollama/Open WebUI/Portainer/Netdata العاملة.

### أمر التحديث الموصى به (يُشغَّل من قِبل حمزة، read-only فقط)

استخدم نفس `AI_SERVER_LAN_IP` ومستخدم SSH الموجودين محلياً عندك (لا تُكتب هنا):

```bash
ssh <user>@<AI_SERVER_LAN_IP> '
echo "--- hostname/whoami ---"; hostname; whoami
echo "--- uname ---"; uname -a
echo "--- os-release ---"; cat /etc/os-release
echo "--- lscpu ---"; lscpu
echo "--- mem ---"; free -h
echo "--- disk ---"; df -h
echo "--- blocks ---"; lsblk
echo "--- gpu ---"; nvidia-smi
echo "--- docker version ---"; docker --version
echo "--- compose version ---"; docker compose version
echo "--- containers ---"; docker ps
echo "--- docker disk usage ---"; docker system df
'
```

نتيجة هذا الأمر تُستخدم لتحديث هذا الملف فقط — **لا تُلصق فيه أي password أو token**.

---

## القيود المهمة (Constraints)

- App Server (هذا الجهاز) لا يشغّل GPU workloads مباشرة — راجع `docs/AI_SERVER_SERVICES_ARCHITECTURE.md`.
- أي TTS/Image/Video engine يجب أن يُختبر على AI Server (وليس على Local Dev Machine) لأن هذا هو العتاد المستهدف فعلياً للتشغيل.
- لا نفترض VRAM/driver/CUDA من الذاكرة لأي قرار — فقط من `nvidia-smi` فعلي حديث.
- لا يجوز تشغيل `docker prune`، إيقاف containers، أو لمس Ollama/Open WebUI/Portainer/Netdata على AI Server إلا بإذن صريح من حمزة لكل عملية.
