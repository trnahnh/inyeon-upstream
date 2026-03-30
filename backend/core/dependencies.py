from functools import lru_cache

from backend.core.config import settings
from backend.services.llm import LLMProvider, create_llm_provider


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Get shared LLM Provider instance based on configuration."""
    return create_llm_provider(
        provider=settings.llm_provider,
        ollama_url=settings.ollama_url,
        ollama_model=settings.ollama_model,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        timeout=settings.ollama_timeout,
    )
