import pytest
from unittest.mock import AsyncMock

from backend.agents.conflict_nodes import (
    parse_conflicts_node,
    resolve_conflicts_node,
    should_continue,
)
from backend.agents.conflict_state import ConflictAgentState
from backend.utils.cost import clear_cache


CONFLICT_CONTENT = """def greet():
<<<<<<< HEAD
    print("Hello from ours")
=======
    print("Hello from theirs")
>>>>>>> branch
"""


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value={
            "resolved_content": 'def greet():\n    print("Hello")\n',
            "strategy": "merge",
            "explanation": "Merged both sides",
        }
    )
    return llm


@pytest.fixture
def initial_state() -> ConflictAgentState:
    return {
        "conflicts": [
            {
                "path": "greet.py",
                "content": CONFLICT_CONTENT,
                "ours": 'def greet():\n    print("Hello from ours")\n',
                "theirs": 'def greet():\n    print("Hello from theirs")\n',
            },
        ],
        "repo_path": ".",
        "resolutions": [],
        "reasoning": [],
        "error": None,
    }


@pytest.fixture
def parsed_state(initial_state) -> ConflictAgentState:
    return initial_state


@pytest.fixture
def error_state(initial_state) -> ConflictAgentState:
    initial_state["error"] = "Previous error"
    return initial_state


class TestParseConflictsNode:

    def setup_method(self):
        clear_cache()

    @pytest.mark.asyncio
    async def test_parse_success(self, initial_state, mock_llm):
        result = await parse_conflicts_node(initial_state, mock_llm)

        assert "conflicts" in result
        assert len(result["conflicts"]) == 1
        assert len(result["reasoning"]) > 0

    @pytest.mark.asyncio
    async def test_parse_empty_conflicts(self, mock_llm):
        state: ConflictAgentState = {
            "conflicts": [],
            "repo_path": ".",
            "resolutions": [],
            "reasoning": [],
            "error": None,
        }
        result = await parse_conflicts_node(state, mock_llm)

        assert "error" in result
        assert "No conflicts provided" in result["error"]

    @pytest.mark.asyncio
    async def test_parse_no_markers(self, mock_llm):
        state: ConflictAgentState = {
            "conflicts": [{"path": "clean.py", "content": "def clean(): pass", "ours": "", "theirs": ""}],
            "repo_path": ".",
            "resolutions": [],
            "reasoning": [],
            "error": None,
        }
        result = await parse_conflicts_node(state, mock_llm)

        assert "error" in result
        assert "No conflict markers" in result["error"]


class TestResolveConflictsNode:

    def setup_method(self):
        clear_cache()

    @pytest.mark.asyncio
    async def test_resolve_success(self, parsed_state, mock_llm):
        result = await resolve_conflicts_node(parsed_state, mock_llm)

        assert "resolutions" in result
        assert len(result["resolutions"]) == 1
        assert result["resolutions"][0]["path"] == "greet.py"
        assert result["resolutions"][0]["strategy"] == "merge"

    @pytest.mark.asyncio
    async def test_resolve_skips_on_error(self, error_state, mock_llm):
        result = await resolve_conflicts_node(error_state, mock_llm)
        assert result == {}

    @pytest.mark.asyncio
    async def test_resolve_handles_llm_error(self, parsed_state, mock_llm):
        mock_llm.generate = AsyncMock(side_effect=Exception("timeout"))
        result = await resolve_conflicts_node(parsed_state, mock_llm)

        assert len(result["resolutions"]) == 1
        assert result["resolutions"][0]["strategy"] == "error"
        assert "failed" in result["resolutions"][0]["explanation"].lower()

    @pytest.mark.asyncio
    async def test_resolve_multiple_files(self, mock_llm):
        state: ConflictAgentState = {
            "conflicts": [
                {"path": "a.py", "content": CONFLICT_CONTENT, "ours": "a", "theirs": "b"},
                {"path": "b.py", "content": CONFLICT_CONTENT, "ours": "c", "theirs": "d"},
            ],
            "repo_path": ".",
            "resolutions": [],
            "reasoning": [],
            "error": None,
        }
        result = await resolve_conflicts_node(state, mock_llm)

        assert len(result["resolutions"]) == 2
        assert mock_llm.generate.call_count == 2


class TestShouldContinue:

    def test_continue_without_error(self, initial_state):
        assert should_continue(initial_state) == "continue"

    def test_error_with_error(self, error_state):
        assert should_continue(error_state) == "error"
