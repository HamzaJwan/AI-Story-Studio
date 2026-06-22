# Ollama Provider Setup

## المطلوب من المستخدم

في `.env`:

```env
OLLAMA_BASE_URL=http://YOUR_OLLAMA_IP:11434
OLLAMA_MODEL=deepseek-r1:7b
```

مثال من بيئة المستخدم:

```env
OLLAMA_BASE_URL=http://192.168.88.3:11434
```

لا تضع هذا المثال كقيمة نهائية داخل repo العام.

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
