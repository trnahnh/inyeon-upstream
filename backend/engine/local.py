"""LocalEngine — runs agents in-process without a backend server."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from backend.models.events import StreamEvent
from .base import EngineResult


class LocalEngine:
    """Execute agents directly in the CLI process."""

    def __init__(
        self,
        llm_provider: str = "ollama",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "qwen2.5-coder:7b",
        gemini_api_key: str | None = None,
        gemini_model: str = "gemini-2.5-flash",
        openai_api_key: str | None = None,
        openai_model: str = "gpt-4.1-mini",
        timeout: int = 120,
    ):
        self._provider_name = llm_provider
        self._ollama_url = ollama_url
        self._ollama_model = ollama_model
        self._gemini_api_key = gemini_api_key
        self._gemini_model = gemini_model
        self._openai_api_key = openai_api_key
        self._openai_model = openai_model
        self._timeout = timeout
        self._llm = None
        self._retriever = None

    def _get_llm(self):
        """Lazy-init LLM provider."""
        if self._llm is None:
            from backend.services.llm.factory import create_llm_provider

            self._llm = create_llm_provider(
                provider=self._provider_name,
                ollama_url=self._ollama_url,
                ollama_model=self._ollama_model,
                gemini_api_key=self._gemini_api_key,
                gemini_model=self._gemini_model,
                openai_api_key=self._openai_api_key,
                openai_model=self._openai_model,
                timeout=self._timeout,
            )
        return self._llm

    def _get_retriever(self):
        """Lazy-init code retriever (returns None if no embeddings available)."""
        if self._retriever is None:
            if not self._gemini_api_key:
                return None
            try:
                from backend.rag import CodeRetriever

                self._retriever = CodeRetriever(api_key=self._gemini_api_key)
            except Exception:
                return None
        return self._retriever

    def _result_from(self, data: dict[str, Any]) -> EngineResult:
        return EngineResult(
            data=data,
            reasoning=data.get("reasoning", []),
            error=data.get("error"),
        )

    def _prepare_diff(self, diff: str, issue_ref: str | None = None) -> str:
        from backend.utils.cost import truncate_diff

        diff = truncate_diff(diff)
        if issue_ref:
            diff = f"{diff}\n\nReference issue: {issue_ref}"
        return diff

    async def generate_commit(
        self, diff: str, repo_path: str = ".", issue_ref: str | None = None
    ) -> EngineResult:
        from backend.agents.commit_agent import CommitAgent

        try:
            agent = CommitAgent(self._get_llm(), self._get_retriever())
            result = await agent.run(
                diff=self._prepare_diff(diff, issue_ref), repo_path=repo_path
            )
            return self._result_from(result)
        except Exception as e:
            return EngineResult(error=str(e))

    async def review(self, diff: str, repo_path: str = ".") -> EngineResult:
        from backend.agents.review_agent import ReviewAgent

        try:
            agent = ReviewAgent(self._get_llm(), self._get_retriever())
            result = await agent.run(diff=self._prepare_diff(diff), repo_path=repo_path)
            return self._result_from(result)
        except Exception as e:
            return EngineResult(error=str(e))

    async def generate_pr(
        self,
        diff: str,
        commits: list[str] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
        repo_path: str = ".",
    ) -> EngineResult:
        from backend.agents.pr_agent import PRAgent

        try:
            agent = PRAgent(self._get_llm(), self._get_retriever())
            result = await agent.run(
                diff=self._prepare_diff(diff),
                commits=commits,
                branch_name=branch_name,
                base_branch=base_branch,
                repo_path=repo_path,
            )
            return self._result_from(result)
        except Exception as e:
            return EngineResult(error=str(e))

    async def split_diff(
        self, diff: str, strategy: str = "hybrid", repo_path: str = "."
    ) -> EngineResult:
        from backend.agents.split_agent import SplitAgent

        try:
            agent = SplitAgent(self._get_llm(), self._get_retriever())
            result = await agent.run(
                diff=self._prepare_diff(diff), repo_path=repo_path, strategy=strategy
            )
            return self._result_from(result)
        except Exception as e:
            return EngineResult(error=str(e))

    async def resolve_conflicts(
        self, conflicts: str, repo_path: str = "."
    ) -> EngineResult:
        from backend.agents.conflict_agent import ConflictAgent

        try:
            agent = ConflictAgent(self._get_llm(), self._get_retriever())
            result = await agent.run(conflicts=conflicts, repo_path=repo_path)
            return self._result_from(result)
        except Exception as e:
            return EngineResult(error=str(e))

    async def generate_changelog(
        self,
        commits: str,
        from_ref: str = "",
        to_ref: str = "HEAD",
        repo_path: str = ".",
    ) -> EngineResult:
        from backend.agents.changelog_agent import ChangelogAgent

        try:
            agent = ChangelogAgent(self._get_llm(), self._get_retriever())
            result = await agent.run(
                commits=commits, from_ref=from_ref, to_ref=to_ref, repo_path=repo_path
            )
            return self._result_from(result)
        except Exception as e:
            return EngineResult(error=str(e))

    async def generate_commit_stream(
        self, diff: str, repo_path: str = ".", issue_ref: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        from backend.agents.commit_agent import CommitAgent

        agent = CommitAgent(self._get_llm(), self._get_retriever())
        async for event in agent.run_stream(
            diff=self._prepare_diff(diff, issue_ref), repo_path=repo_path
        ):
            yield event

    async def review_stream(
        self, diff: str, repo_path: str = "."
    ) -> AsyncIterator[StreamEvent]:
        from backend.agents.review_agent import ReviewAgent

        agent = ReviewAgent(self._get_llm(), self._get_retriever())
        async for event in agent.run_stream(
            diff=self._prepare_diff(diff), repo_path=repo_path
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
        from backend.agents.pr_agent import PRAgent

        agent = PRAgent(self._get_llm(), self._get_retriever())
        async for event in agent.run_stream(
            diff=self._prepare_diff(diff),
            commits=commits,
            branch_name=branch_name,
            base_branch=base_branch,
            repo_path=repo_path,
        ):
            yield event

    async def split_diff_stream(
        self, diff: str, strategy: str = "hybrid", repo_path: str = "."
    ) -> AsyncIterator[StreamEvent]:
        from backend.agents.split_agent import SplitAgent

        agent = SplitAgent(self._get_llm(), self._get_retriever())
        async for event in agent.run_stream(
            diff=self._prepare_diff(diff), repo_path=repo_path, strategy=strategy
        ):
            yield event

    async def resolve_conflicts_stream(
        self, conflicts: str, repo_path: str = "."
    ) -> AsyncIterator[StreamEvent]:
        from backend.agents.conflict_agent import ConflictAgent

        agent = ConflictAgent(self._get_llm(), self._get_retriever())
        async for event in agent.run_stream(conflicts=conflicts, repo_path=repo_path):
            yield event

    async def generate_changelog_stream(
        self,
        commits: str,
        from_ref: str = "",
        to_ref: str = "HEAD",
        repo_path: str = ".",
    ) -> AsyncIterator[StreamEvent]:
        from backend.agents.changelog_agent import ChangelogAgent

        agent = ChangelogAgent(self._get_llm(), self._get_retriever())
        async for event in agent.run_stream(
            commits=commits, from_ref=from_ref, to_ref=to_ref, repo_path=repo_path
        ):
            yield event
