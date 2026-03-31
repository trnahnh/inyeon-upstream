from fastapi import Request

from backend.core.config import settings
from backend.services.llm import LLMProvider, create_llm_provider, ProviderConfigError

_providers: dict[str, LLMProvider] = {}


def _get_or_create_provider(name: str) -> LLMProvider:
    if name not in _providers:
        _providers[name] = create_llm_provider(
            provider=name,
            ollama_url=settings.ollama_url,
            ollama_model=settings.ollama_model,
            gemini_api_key=settings.gemini_api_key,
            gemini_model=settings.gemini_model,
            openai_api_key=settings.openai_api_key,
            openai_model=settings.openai_model,
            timeout=settings.ollama_timeout,
        )
    return _providers[name]


def get_llm_provider() -> LLMProvider:
    return _get_or_create_provider(settings.llm_provider)


def get_llm_from_request(request: Request) -> LLMProvider:
    provider_name = request.headers.get("X-LLM-Provider", settings.llm_provider)
    try:
        return _get_or_create_provider(provider_name)
    except (ProviderConfigError, ValueError) as e:
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
