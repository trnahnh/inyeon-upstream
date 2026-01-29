from enum import Enum

from .base import LLMProvider
from .ollama import OllamaProvider
from .gemini import GeminiProvider


class ProviderType(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"


class ProviderConfigError(Exception):
    """Raised when provider configuration is invalid."""

    pass


def create_llm_provider(
    provider: ProviderType | str,
    ollama_url: str | None = None,
    ollama_model: str | None = None,
    gemini_api_key: str | None = None,
    gemini_model: str | None = None,
    timeout: int = 120,
) -> LLMProvider:
    """
    Factory function to create LLM providers.

    Args:
        provider: Which provider to use (ollama, gemini)
        ollama_url: Ollama server URL
        ollama_model: Ollama model name
        gemini_api_key: Gemini API key
        gemini_model: Gemini model name
        timeout: Request timeout in seconds

    Returns:
        Configured LLMProvider instance

    Raises:
        ProviderConfigError: If required config is missing
    """
    provider = ProviderType(provider)

    if provider == ProviderType.OLLAMA:
        if not ollama_url or not ollama_model:
            raise ProviderConfigError("Ollama requires url and model")
        return OllamaProvider(
            base_url=ollama_url,
            model=ollama_model,
            timeout=timeout,
        )

    if provider == ProviderType.GEMINI:
        if not gemini_api_key:
            raise ProviderConfigError("Gemini requires api_key")
        return GeminiProvider(
            api_key=gemini_api_key,
            model=gemini_model or "gemini-2.5-flash",
            timeout=timeout,
        )
