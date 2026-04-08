from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INYEON_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_url: str = "https://inyeon-upstream-production.up.railway.app"
    timeout: int = 120
    api_key: str | None = None
    llm_provider: str | None = None

    default_format: str = "rich"

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    ollama_timeout: int = 120
    max_diff_chars: int = 30000


def get_config_file() -> Path | None:
    paths = [
        Path.cwd() / ".inyeon.toml",
        Path.home() / ".config" / "inyeon" / "config.toml",
    ]

    for path in paths:
        if path.exists():
            return path

    return None


settings = Settings()
