from importlib.metadata import version, PackageNotFoundError

from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    _pkg_version = version("inyeon")
except PackageNotFoundError:
    _pkg_version = "3.5.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INYEON_")

    llm_provider: str = "ollama"

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_timeout: int = 120

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    api_title: str = "Inyeon API"
    api_version: str = _pkg_version
    debug: bool = False

    max_diff_chars: int = 30000
    enable_cache: bool = True

    api_key: str | None = None
    cors_origins: str = "*"
    rate_limit_rpm: int = 30


settings = Settings()
