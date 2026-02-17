import pytest
from unittest.mock import AsyncMock

from backend.agents.changelog_nodes import (
    group_commits_node,
    generate_changelog_node,
    should_continue,
    _extract_type,
)
from backend.agents.changelog_state import ChangelogAgentState
from backend.utils.cost import clear_cache


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value={
            "version": "3.0.0",
            "date": "2026-02-17",
            "sections": {"feat": ["New feature"]},
            "summary": "Release summary.",
        }
    )
    return llm


@pytest.fixture
def initial_state() -> ChangelogAgentState:
    return {
        "commits": [
            {"hash": "abc123", "subject": "feat(auth): add login", "body": "", "author": "dev", "date": "2026-02-15"},
            {"hash": "def456", "subject": "fix: resolve crash", "body": "", "author": "dev", "date": "2026-02-16"},
            {"hash": "ghi789", "subject": "docs: update readme", "body": "", "author": "dev", "date": "2026-02-17"},
        ],
        "from_ref": "v2.0.0",
        "to_ref": "HEAD",
        "repo_path": ".",
        "grouped_commits": {},
        "changelog": None,
        "reasoning": [],
        "error": None,
    }


@pytest.fixture
def grouped_state(initial_state) -> ChangelogAgentState:
    initial_state["grouped_commits"] = {
        "feat": [{"hash": "abc123", "subject": "feat(auth): add login", "body": "", "author": "dev"}],
        "fix": [{"hash": "def456", "subject": "fix: resolve crash", "body": "", "author": "dev"}],
    }
    return initial_state


@pytest.fixture
def error_state(initial_state) -> ChangelogAgentState:
    initial_state["error"] = "Previous error"
    return initial_state


class TestGroupCommitsNode:

    def setup_method(self):
        clear_cache()

    @pytest.mark.asyncio
    async def test_group_success(self, initial_state, mock_llm):
        result = await group_commits_node(initial_state, mock_llm)

        assert "grouped_commits" in result
        assert "feat" in result["grouped_commits"]
        assert "fix" in result["grouped_commits"]
        assert "docs" in result["grouped_commits"]
        assert len(result["reasoning"]) > 0

    @pytest.mark.asyncio
    async def test_group_empty_commits(self, mock_llm):
        state: ChangelogAgentState = {
            "commits": [],
            "from_ref": "",
            "to_ref": "HEAD",
            "repo_path": ".",
            "grouped_commits": {},
            "changelog": None,
            "reasoning": [],
            "error": None,
        }
        result = await group_commits_node(state, mock_llm)

        assert "error" in result
        assert "No commits provided" in result["error"]

    @pytest.mark.asyncio
    async def test_group_unknown_type_defaults_to_chore(self, mock_llm):
        state: ChangelogAgentState = {
            "commits": [{"hash": "abc", "subject": "random message", "body": "", "author": "dev", "date": "2026-01-01"}],
            "from_ref": "",
            "to_ref": "HEAD",
            "repo_path": ".",
            "grouped_commits": {},
            "changelog": None,
            "reasoning": [],
            "error": None,
        }
        result = await group_commits_node(state, mock_llm)

        assert "chore" in result["grouped_commits"]


class TestGenerateChangelogNode:

    def setup_method(self):
        clear_cache()

    @pytest.mark.asyncio
    async def test_generate_success(self, grouped_state, mock_llm):
        result = await generate_changelog_node(grouped_state, mock_llm)

        assert "changelog" in result
        assert result["changelog"]["version"] == "3.0.0"

    @pytest.mark.asyncio
    async def test_generate_skips_on_error(self, error_state, mock_llm):
        result = await generate_changelog_node(error_state, mock_llm)
        assert result == {}

    @pytest.mark.asyncio
    async def test_generate_handles_llm_error(self, grouped_state, mock_llm):
        mock_llm.generate = AsyncMock(side_effect=Exception("timeout"))
        result = await generate_changelog_node(grouped_state, mock_llm)

        assert "error" in result
        assert "generation failed" in result["error"].lower()


class TestShouldContinue:

    def test_continue_without_error(self, initial_state):
        assert should_continue(initial_state) == "continue"

    def test_error_with_error(self, error_state):
        assert should_continue(error_state) == "error"


class TestExtractType:

    def test_feat(self):
        assert _extract_type("feat: add feature") == "feat"

    def test_feat_with_scope(self):
        assert _extract_type("feat(auth): add login") == "feat"

    def test_fix(self):
        assert _extract_type("fix: resolve crash") == "fix"

    def test_docs(self):
        assert _extract_type("docs: update readme") == "docs"

    def test_unknown_defaults_to_chore(self):
        assert _extract_type("random commit message") == "chore"

    def test_breaking_change(self):
        assert _extract_type("feat!: breaking change") == "feat"
