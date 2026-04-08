"""Engine factory for CLI — creates LocalEngine or HttpEngine based on --local flag."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol


class PipelineBackend(Protocol):
    """Protocol that both APIClient and SyncLocalBackend satisfy."""

    def split_diff(self, diff: str, strategy: str = "hybrid", repo_path: str = ".") -> dict: ...
    def generate_commit(self, diff: str, issue_ref: str | None = None) -> dict: ...
    def review(self, diff: str) -> dict: ...
    def generate_pr(
        self,
        diff: str,
        commits: list[dict[str, str]] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
    ) -> dict: ...


def create_engine(
    local: bool = False,
    api_url: str | None = None,
    api_key: str | None = None,
    provider: str | None = None,
):
    """Create the appropriate execution engine.

    Returns LocalEngine (async) if local=True, else HttpEngine (async).
    """
    if local:
        from backend.engine.local import LocalEngine
        from cli.config import settings

        return LocalEngine(
            llm_provider=provider or settings.llm_provider or "ollama",
            ollama_url=settings.ollama_url,
            ollama_model=settings.ollama_model,
            gemini_api_key=settings.gemini_api_key,
            gemini_model=settings.gemini_model,
            openai_api_key=settings.openai_api_key,
            openai_model=settings.openai_model,
            timeout=settings.ollama_timeout,
        )
    else:
        from backend.engine.http import HttpEngine
        from cli.api_client import APIClient

        client = APIClient(base_url=api_url, api_key=api_key, provider=provider)
        return HttpEngine(client)


class SyncLocalBackend:
    """Sync wrapper around LocalEngine for Pipeline compatibility."""

    def __init__(self, engine):
        self._engine = engine

    def split_diff(self, diff: str, strategy: str = "hybrid", repo_path: str = ".") -> dict:
        result = asyncio.run(self._engine.split_diff(diff, strategy, repo_path))
        return result.data if not result.error else {"error": result.error, "splits": []}

    def generate_commit(self, diff: str, issue_ref: str | None = None) -> dict:
        result = asyncio.run(self._engine.generate_commit(diff, issue_ref=issue_ref))
        return result.data if not result.error else {"error": result.error}

    def review(self, diff: str) -> dict:
        result = asyncio.run(self._engine.review(diff))
        return result.data if not result.error else {"error": result.error}

    def generate_pr(
        self,
        diff: str,
        commits: list[dict[str, str]] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
    ) -> dict:
        result = asyncio.run(
            self._engine.generate_pr(diff, commits, branch_name, base_branch)
        )
        return result.data if not result.error else {"error": result.error}
