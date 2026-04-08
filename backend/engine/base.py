from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from backend.models.events import StreamEvent


@dataclass
class EngineResult:
    """Result from an engine operation."""

    data: dict[str, Any] = field(default_factory=dict)
    reasoning: list[str] = field(default_factory=list)
    error: str | None = None


@runtime_checkable
class ExecutionEngine(Protocol):
    """Protocol for agent execution engines.

    Both HttpEngine (remote backend) and LocalEngine (in-process)
    implement this interface so the CLI can swap between them.
    """

    async def generate_commit(
        self, diff: str, repo_path: str = ".", issue_ref: str | None = None
    ) -> EngineResult: ...

    async def review(
        self, diff: str, repo_path: str = "."
    ) -> EngineResult: ...

    async def generate_pr(
        self,
        diff: str,
        commits: list[str] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
        repo_path: str = ".",
    ) -> EngineResult: ...

    async def split_diff(
        self, diff: str, strategy: str = "hybrid", repo_path: str = "."
    ) -> EngineResult: ...

    async def resolve_conflicts(
        self, conflicts: str, repo_path: str = "."
    ) -> EngineResult: ...

    async def generate_changelog(
        self,
        commits: str,
        from_ref: str = "",
        to_ref: str = "HEAD",
        repo_path: str = ".",
    ) -> EngineResult: ...

    async def generate_commit_stream(
        self, diff: str, repo_path: str = ".", issue_ref: str | None = None
    ) -> AsyncIterator[StreamEvent]: ...

    async def review_stream(
        self, diff: str, repo_path: str = "."
    ) -> AsyncIterator[StreamEvent]: ...

    async def generate_pr_stream(
        self,
        diff: str,
        commits: list[str] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
        repo_path: str = ".",
    ) -> AsyncIterator[StreamEvent]: ...

    async def split_diff_stream(
        self, diff: str, strategy: str = "hybrid", repo_path: str = "."
    ) -> AsyncIterator[StreamEvent]: ...

    async def resolve_conflicts_stream(
        self, conflicts: str, repo_path: str = "."
    ) -> AsyncIterator[StreamEvent]: ...

    async def generate_changelog_stream(
        self,
        commits: str,
        from_ref: str = "",
        to_ref: str = "HEAD",
        repo_path: str = ".",
    ) -> AsyncIterator[StreamEvent]: ...
