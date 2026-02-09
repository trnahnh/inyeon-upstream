import pytest
from unittest.mock import AsyncMock

from backend.agents.split_nodes import (
    parse_diff_node,
    cluster_hunks_node,
    generate_messages_node,
    should_continue,
    _get_strategy,
)
from backend.agents.split_state import SplitAgentState
from backend.clustering import DirectoryStrategy, ConventionalStrategy, HybridStrategy


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value={
            "type": "feat",
            "scope": None,
            "subject": "add feature",
            "message": "feat: add feature",
        }
    )
    return llm


@pytest.fixture
def sample_diff():
    return """diff --git a/main.py b/main.py
index 1234567..abcdefg 100644
--- a/main.py
+++ b/main.py
@@ -1,3 +1,4 @@
 def main():
+    print("Hello")
     pass
     return
"""


@pytest.fixture
def initial_state(sample_diff) -> SplitAgentState:
    return {
        "diff": sample_diff,
        "repo_path": ".",
        "strategy": "directory",
        "parsed_diff": None,
        "commit_groups": [],
        "generated_messages": {},
        "splits": [],
        "reasoning": [],
        "error": None,
    }


@pytest.fixture
def error_state(sample_diff) -> SplitAgentState:
    return {
        "diff": sample_diff,
        "repo_path": ".",
        "strategy": "directory",
        "parsed_diff": None,
        "commit_groups": [],
        "generated_messages": {},
        "splits": [],
        "reasoning": [],
        "error": "Previous error",
    }


class TestParseDiffNode:

    @pytest.mark.asyncio
    async def test_parse_diff_success(self, initial_state):
        result = await parse_diff_node(initial_state)

        assert "parsed_diff" in result
        assert result["parsed_diff"] is not None
        assert "error" not in result or result.get("error") is None
        assert len(result["reasoning"]) > 0

    @pytest.mark.asyncio
    async def test_parse_diff_empty(self):
        state: SplitAgentState = {
            "diff": "",
            "repo_path": ".",
            "strategy": "directory",
            "parsed_diff": None,
            "commit_groups": [],
            "generated_messages": {},
            "splits": [],
            "reasoning": [],
            "error": None,
        }
        result = await parse_diff_node(state)

        assert result["parsed_diff"] is not None
        assert len(result["parsed_diff"].files) == 0

    @pytest.mark.asyncio
    async def test_parse_diff_adds_reasoning(self, initial_state):
        result = await parse_diff_node(initial_state)

        assert any("Parsed diff" in r for r in result["reasoning"])


class TestClusterHunksNode:

    @pytest.mark.asyncio
    async def test_cluster_skips_on_error(self, error_state, mock_llm):
        result = await cluster_hunks_node(error_state, mock_llm, None)

        assert result == {}

    @pytest.mark.asyncio
    async def test_cluster_creates_groups(self, initial_state, mock_llm):
        parse_result = await parse_diff_node(initial_state)
        initial_state.update(parse_result)

        result = await cluster_hunks_node(initial_state, mock_llm, None)

        assert "commit_groups" in result
        assert len(result["commit_groups"]) > 0

    @pytest.mark.asyncio
    async def test_cluster_adds_reasoning(self, initial_state, mock_llm):
        parse_result = await parse_diff_node(initial_state)
        initial_state.update(parse_result)

        result = await cluster_hunks_node(initial_state, mock_llm, None)

        assert any("commit groups" in r for r in result["reasoning"])


class TestGenerateMessagesNode:

    @pytest.mark.asyncio
    async def test_generate_skips_on_error(self, error_state, mock_llm):
        result = await generate_messages_node(error_state, mock_llm)

        assert result == {}

    @pytest.mark.asyncio
    async def test_generate_creates_messages(self, initial_state, mock_llm):
        parse_result = await parse_diff_node(initial_state)
        initial_state.update(parse_result)

        cluster_result = await cluster_hunks_node(initial_state, mock_llm, None)
        initial_state.update(cluster_result)

        result = await generate_messages_node(initial_state, mock_llm)

        assert "splits" in result
        assert "generated_messages" in result
        assert len(result["splits"]) > 0

    @pytest.mark.asyncio
    async def test_generate_split_structure(self, initial_state, mock_llm):
        parse_result = await parse_diff_node(initial_state)
        initial_state.update(parse_result)

        cluster_result = await cluster_hunks_node(initial_state, mock_llm, None)
        initial_state.update(cluster_result)

        result = await generate_messages_node(initial_state, mock_llm)

        for split in result["splits"]:
            assert "group_id" in split
            assert "files" in split
            assert "hunk_count" in split
            assert "commit_message" in split
            assert "commit_type" in split


class TestShouldContinue:

    def test_should_continue_with_error(self, error_state):
        result = should_continue(error_state)
        assert result == "error"

    def test_should_continue_without_error(self, initial_state):
        result = should_continue(initial_state)
        assert result == "continue"


class TestGetStrategy:

    def test_get_directory_strategy(self, mock_llm):
        strategy = _get_strategy("directory", mock_llm, None)
        assert isinstance(strategy, DirectoryStrategy)

    def test_get_conventional_strategy(self, mock_llm):
        strategy = _get_strategy("conventional", mock_llm, None)
        assert isinstance(strategy, ConventionalStrategy)

    def test_get_hybrid_strategy(self, mock_llm):
        strategy = _get_strategy("hybrid", mock_llm, None)
        assert isinstance(strategy, HybridStrategy)

    def test_get_invalid_strategy_defaults_to_hybrid(self, mock_llm):
        strategy = _get_strategy("invalid", mock_llm, None)
        assert isinstance(strategy, HybridStrategy)
