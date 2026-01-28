from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Prefix: INYEON_
    Example: INYEON_OLLAMA_URL=http://localhost:11434
    """

    model_config = SettingsConfigDict(
        env_prefix="INYEON_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama Configuration
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_timeout: int = 120

    # API Configuration
    api_title: str = "Inyeon API"
    api_version: str = "0.1.0"
    debug: bool = False


# Global settings instance
settings = Settings()
