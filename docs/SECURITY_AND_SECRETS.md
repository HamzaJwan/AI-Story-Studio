# Security and Secrets SOP

## لا أسرار في Git

ممنوع وضع:
- API keys
- passwords
- database URLs
- real tokens
- SSH keys
- Cloudflare tokens
- real production IPs if sensitive

## أين نضع الأسرار؟

- Local: `.env` فقط، وهو داخل `.gitignore`.
- Production: Portainer Environment Variables أو Secret Manager.
- GitHub Actions: GitHub Secrets.

## Frontend Rule

الـ frontend لا يحتوي مفاتيح AI.  
كل استدعاء AI يمر عبر backend.

## Logging Rule

لا تطبع:
- prompt كامل إذا كان حساساً.
- مفاتيح.
- headers.
- tokens.
- ملفات صوت أو مسارات خاصة بشكل يضر الخصوصية.

## AI Output Warning

كل نتيجة AI تعرض للمستخدم مع:
- مصدرها.
- النموذج.
- حدودها.
- قابلية التعديل قبل الاعتماد.
