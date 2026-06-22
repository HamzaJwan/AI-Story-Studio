# Ollama Provider Setup

## المطلوب من المستخدم

في `.env`:

```env
OLLAMA_BASE_URL=http://AI_SERVER_LAN_IP:11434
OLLAMA_MODEL=qwen2.5:7b
```

مثال آمن بدون IP حقيقي:

```env
OLLAMA_BASE_URL=http://AI_SERVER_LAN_IP:11434
```

- لا تضع IP الحقيقي داخل Git.
- القيمة الحقيقية توضع في `.env` المحلي فقط.
- في Docker Desktop على Windows، إذا كان Ollama على سيرفر LAN استخدم LAN URL في `.env`.
- إذا كان Ollama داخل نفس docker network لاحقاً، يمكن استخدام service name مثل `http://ollama:11434`.

## Health Check

Codex يجب أن ينشئ endpoint:

```text
GET /api/ai/ollama/health
```

يرجع:

```json
{
  "ok": true,
  "provider": "ollama",
  "base_url_configured": true,
  "model": "deepseek-r1:7b",
  "latency_ms": 123
}
```

## Generate Endpoint في Ollama

المبدأ:

```http
POST {OLLAMA_BASE_URL}/api/generate
```

Payload:

```json
{
  "model": "deepseek-r1:7b",
  "prompt": "...",
  "stream": false,
  "options": {
    "temperature": 0.2,
    "num_ctx": 8192
  }
}
```

## JSON Output Rule

لا تثق أن النموذج سيعيد JSON نظيف دائماً.

Backend يجب أن:
1. يطلب JSON فقط.
2. يستخرج JSON من النص.
3. يتحقق من الحقول المطلوبة.
4. يرجع خطأ واضح لو JSON غير صالح.
