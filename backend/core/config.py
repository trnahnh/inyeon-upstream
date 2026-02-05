from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Prefix: INYEON_
    Example: INYEON_OLLAMA_URL=ollama
    """

    model_config = SettingsConfigDict(env_prefix="INYEON_")

    # LLM Provider Selection
    llm_provider: str = "ollama"

    # Ollama Configuration
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_timeout: int = 120

    # Gemini Configuration
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # API Configuration
    api_title: str = "Inyeon API"
    api_version: str = "2.0.0"
    debug: bool = False


# Global settings instance
settings = Settings()
