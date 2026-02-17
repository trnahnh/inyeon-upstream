import pytest
from unittest.mock import AsyncMock

from backend.agents.changelog_agent import ChangelogAgent
from backend.utils.cost import clear_cache


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value={
            "version": "3.0.0",
            "date": "2026-02-17",
            "sections": {
                "feat": ["Add session management", "Add pipeline orchestration"],
                "fix": ["Fix auth timeout"],
            },
            "summary": "Major release with new features and bug fixes.",
        }
    )
    return llm


@pytest.fixture
def sample_commits():
    return [
        {"hash": "abc12345", "subject": "feat(auth): add session creation", "body": "", "author": "dev", "date": "2026-02-15"},
        {"hash": "def67890", "subject": "fix(auth): fix timeout", "body": "", "author": "dev", "date": "2026-02-16"},
        {"hash": "ghi11111", "subject": "feat: add pipeline", "body": "", "author": "dev", "date": "2026-02-17"},
    ]


class TestChangelogAgent:

    def setup_method(self):
        clear_cache()

    @pytest.mark.asyncio
    async def test_changelog_agent_init(self, mock_llm):
        agent = ChangelogAgent(llm=mock_llm, retriever=None)
        assert agent.name == "changelog"
        assert agent.graph is not None

    @pytest.mark.asyncio
    async def test_changelog_agent_run(self, mock_llm, sample_commits):
        agent = ChangelogAgent(llm=mock_llm, retriever=None)
        result = await agent.run(commits=sample_commits, from_ref="v2.0.0", to_ref="HEAD")

        assert "changelog" in result
        assert "reasoning" in result
        assert result["error"] is None
        assert result["changelog"] is not None

    @pytest.mark.asyncio
    async def test_changelog_agent_empty_commits(self, mock_llm):
        agent = ChangelogAgent(llm=mock_llm, retriever=None)
        result = await agent.run(commits=[])

        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_changelog_agent_reasoning_tracked(self, mock_llm, sample_commits):
        agent = ChangelogAgent(llm=mock_llm, retriever=None)
        result = await agent.run(commits=sample_commits)

        assert len(result["reasoning"]) >= 2

    @pytest.mark.asyncio
    async def test_changelog_agent_handles_llm_error(self, mock_llm, sample_commits):
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM down"))
        agent = ChangelogAgent(llm=mock_llm, retriever=None)
        result = await agent.run(commits=sample_commits)

        assert result["error"] is not None
        assert "generation failed" in result["error"].lower()
