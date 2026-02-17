import pytest
from unittest.mock import AsyncMock

from backend.agents.pr_nodes import (
    analyze_branch_node,
    generate_pr_node,
    should_continue,
)
from backend.agents.pr_state import PRAgentState
from backend.utils.cost import clear_cache


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value={
            "scope": "authentication system",
            "change_types": ["feat"],
            "key_changes": ["Add session management"],
            "has_breaking_changes": False,
            "has_tests": True,
            "affected_areas": ["auth"],
        }
    )
    return llm


@pytest.fixture
def initial_state() -> PRAgentState:
    return {
        "diff": "diff --git a/f.py b/f.py\n+new line\n",
        "commits": [
            {"hash": "abc123", "subject": "feat: add feature", "body": "", "author": "dev"},
        ],
        "branch_name": "feature/test",
        "base_branch": "main",
        "repo_path": ".",
        "analysis": None,
        "pr_description": None,
        "reasoning": [],
        "error": None,
    }


@pytest.fixture
def analyzed_state(initial_state) -> PRAgentState:
    initial_state["analysis"] = {
        "scope": "test feature",
        "change_types": ["feat"],
        "key_changes": ["Add feature"],
        "has_breaking_changes": False,
        "has_tests": False,
        "affected_areas": ["core"],
    }
    return initial_state


@pytest.fixture
def error_state(initial_state) -> PRAgentState:
    initial_state["error"] = "Previous error"
    return initial_state


class TestAnalyzeBranchNode:

    def setup_method(self):
        clear_cache()

    @pytest.mark.asyncio
    async def test_analyze_success(self, initial_state, mock_llm):
        result = await analyze_branch_node(initial_state, mock_llm)

        assert "analysis" in result
        assert result["analysis"] is not None
        assert len(result["reasoning"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_uses_cache(self, initial_state, mock_llm):
        await analyze_branch_node(initial_state, mock_llm)
        result = await analyze_branch_node(initial_state, mock_llm)

        assert "cached" in result["reasoning"][-1].lower()
        assert mock_llm.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_analyze_handles_error(self, initial_state, mock_llm):
        mock_llm.generate = AsyncMock(side_effect=Exception("API error"))
        result = await analyze_branch_node(initial_state, mock_llm)

        assert "error" in result
        assert "Analysis failed" in result["error"]


class TestGeneratePRNode:

    def setup_method(self):
        clear_cache()

    @pytest.mark.asyncio
    async def test_generate_success(self, analyzed_state, mock_llm):
        mock_llm.generate = AsyncMock(
            return_value={
                "title": "feat: add feature",
                "summary": "Adds a new feature.",
                "changes": ["- Add feature"],
                "testing": "Run tests",
                "breaking_changes": [],
            }
        )
        result = await generate_pr_node(analyzed_state, mock_llm)

        assert "pr_description" in result
        assert result["pr_description"]["title"] == "feat: add feature"

    @pytest.mark.asyncio
    async def test_generate_skips_on_error(self, error_state, mock_llm):
        result = await generate_pr_node(error_state, mock_llm)
        assert result == {}

    @pytest.mark.asyncio
    async def test_generate_handles_llm_error(self, analyzed_state, mock_llm):
        mock_llm.generate = AsyncMock(side_effect=Exception("timeout"))
        result = await generate_pr_node(analyzed_state, mock_llm)

        assert "error" in result
        assert "PR generation failed" in result["error"]


class TestShouldContinue:

    def test_continue_without_error(self, initial_state):
        assert should_continue(initial_state) == "continue"

    def test_error_with_error(self, error_state):
        assert should_continue(error_state) == "error"
