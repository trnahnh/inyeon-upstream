"""HttpEngine — wraps APIClient for remote agent execution."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from backend.models.events import EventType, StreamEvent
from .base import EngineResult

if TYPE_CHECKING:
    from cli.api_client import APIClient


class HttpEngine:
    """Execute agents via HTTP against a running backend server."""

    def __init__(self, client: APIClient):
        self._client = client

    def _result_from(self, data: dict) -> EngineResult:
        return EngineResult(
            data=data,
            reasoning=data.get("reasoning", []),
            error=data.get("error"),
        )

    async def _run_sync(self, fn, *args, **kwargs) -> EngineResult:
        data = await asyncio.to_thread(fn, *args, **kwargs)
        return self._result_from(data)

    async def _stream_to_async(self, sync_iter) -> AsyncIterator[StreamEvent]:
        """Bridge sync SSE iterator to async StreamEvent iterator."""
        import queue
        import threading

        _SENTINEL = object()
        q: queue.Queue = queue.Queue()

        def _consume():
            try:
                for item in sync_iter:
                    q.put(item)
            except Exception as exc:
                q.put(exc)
            finally:
                q.put(_SENTINEL)

        thread = threading.Thread(target=_consume, daemon=True)
        thread.start()

        while True:
            item = await asyncio.to_thread(q.get)
            if item is _SENTINEL:
                break
            if isinstance(item, Exception):
                raise item
            yield StreamEvent(**item)

    async def generate_commit(
        self, diff: str, repo_path: str = ".", issue_ref: str | None = None
    ) -> EngineResult:
        return await self._run_sync(
            self._client.generate_commit, diff, issue_ref
        )

    async def review(self, diff: str, repo_path: str = ".") -> EngineResult:
        return await self._run_sync(self._client.review, diff)

    async def generate_pr(
        self,
        diff: str,
        commits: list[str] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
        repo_path: str = ".",
    ) -> EngineResult:
        return await self._run_sync(
            self._client.generate_pr, diff, commits, branch_name, base_branch
        )

    async def split_diff(
        self, diff: str, strategy: str = "hybrid", repo_path: str = "."
    ) -> EngineResult:
        return await self._run_sync(
            self._client.split_diff, diff, strategy, repo_path
        )

    async def resolve_conflicts(
        self, conflicts: str, repo_path: str = "."
    ) -> EngineResult:
        return await self._run_sync(self._client.resolve_conflicts, conflicts)

    async def generate_changelog(
        self,
        commits: str,
        from_ref: str = "",
        to_ref: str = "HEAD",
        repo_path: str = ".",
    ) -> EngineResult:
        return await self._run_sync(
            self._client.generate_changelog, commits, from_ref, to_ref
        )

    async def generate_commit_stream(
        self, diff: str, repo_path: str = ".", issue_ref: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        async for event in self._stream_to_async(
            self._client.generate_commit_stream(diff, repo_path, issue_ref)
        ):
            yield event

    async def review_stream(
        self, diff: str, repo_path: str = "."
    ) -> AsyncIterator[StreamEvent]:
        async for event in self._stream_to_async(
            self._client.review_stream(diff, repo_path)
        ):
            yield event

    async def generate_pr_stream(
        self,
        diff: str,
        commits: list[str] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
        repo_path: str = ".",
    ) -> AsyncIterator[StreamEvent]:
        async for event in self._stream_to_async(
            self._client.generate_pr_stream(diff, commits, branch_name, base_branch)
        ):
            yield event

    async def split_diff_stream(
        self, diff: str, strategy: str = "hybrid", repo_path: str = "."
    ) -> AsyncIterator[StreamEvent]:
        async for event in self._stream_to_async(
            self._client.split_diff_stream(diff, strategy, repo_path)
        ):
            yield event

    async def resolve_conflicts_stream(
        self, conflicts: str, repo_path: str = "."
    ) -> AsyncIterator[StreamEvent]:
        async for event in self._stream_to_async(
            self._client.resolve_conflicts_stream(conflicts)
        ):
            yield event

    async def generate_changelog_stream(
        self,
        commits: str,
        from_ref: str = "",
        to_ref: str = "HEAD",
        repo_path: str = ".",
    ) -> AsyncIterator[StreamEvent]:
        async for event in self._stream_to_async(
            self._client.generate_changelog_stream(commits, from_ref, to_ref)
        ):
            yield event
