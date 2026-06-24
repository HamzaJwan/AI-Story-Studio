# AllTalk AI Server Service Benchmark Lab

This lab is a service-based benchmark scaffold for an external AllTalk/XTTS-compatible TTS service.

It does not copy AllTalk source code into AI Story Studio, does not modify the backend/frontend, and does not expose any service by itself.

## Scope

- Test an already running AllTalk service over LAN.
- Keep TTS engine evaluation separate from the main app.
- Use placeholders only; do not commit real LAN IPs or credentials.
- Do not use celebrity voices or real-person voices without explicit permission.

## Safety Rules

- Do not use famous voices, presenter voices, reciter voices, or celebrity samples.
- Do not use a real person's voice without explicit permission.
- Use only a licensed, owned, or otherwise safe test voice.
- Keep generated WAV/MP3 outputs out of Git.

## Configuration

Copy the example file if needed:

```bash
cp .env.example .env
```

Set `TTS_SERVICE_URL` to the private LAN URL of the AllTalk service:

```env
TTS_SERVICE_URL=http://AI_SERVER_IP:7851
```

Do not commit `.env`.

## Benchmark

From this folder:

```bash
./benchmark_alltalk.sh
```

The script checks:

1. `GET /api/ready`
2. `GET /api/voices`
3. `POST /api/tts-generate`

## Expected Outcome

A passing service should report readiness, return available voices, and generate audio through `/api/tts-generate` using a safe configured voice.

## Current Decision

AllTalk/XTTS is a candidate fallback TTS service. It should be tested as an external AI Server service before any AI Story Studio backend integration is designed.
