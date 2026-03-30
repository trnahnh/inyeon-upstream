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

    default_format: str = "rich"


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
