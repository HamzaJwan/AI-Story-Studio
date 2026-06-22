from fastapi import APIRouter, Depends

from app.ai_providers.ollama import OllamaError, OllamaProvider
from app.config import Settings, get_settings
from app.schemas import ApiEnvelope, OllamaTestRequest

router = APIRouter(tags=["ollama"])


def get_provider(settings: Settings = Depends(get_settings)) -> OllamaProvider:
    return OllamaProvider(settings)


@router.post("/api/ollama/test", response_model=ApiEnvelope)
def test_ollama(
    request: OllamaTestRequest | None = None,
    provider: OllamaProvider = Depends(get_provider),
) -> ApiEnvelope:
    try:
        result = provider.generate_text(
            prompt="Reply with OK only.",
            model=request.model if request else None,
            temperature=0,
            num_ctx=256,
            num_predict=8,
        )
        return ApiEnvelope(
            data={
                "connected": True,
                "latency_ms": result.latency_ms,
                "model": result.model,
            },
            meta={"provider": "ollama"},
        )
    except OllamaError as exc:
        return ApiEnvelope(
            data={
                "connected": False,
                "latency_ms": None,
                "model": provider.model,
            },
            meta={"provider": "ollama"},
            errors=[str(exc)],
        )


@router.get("/api/ai/ollama/health", response_model=ApiEnvelope)
def ollama_health(provider: OllamaProvider = Depends(get_provider)) -> ApiEnvelope:
    data = provider.health()
    errors = [] if data["ok"] else ["Ollama is not reachable or not configured."]
    return ApiEnvelope(data=data, meta={"provider": "ollama"}, errors=errors)
