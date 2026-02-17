import pytest
from unittest.mock import AsyncMock

from backend.agents.split_agent import SplitAgent
from backend.agents.split_state import SplitAgentState


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value={
            "type": "feat",
            "scope": "agents",
            "subject": "add new feature",
            "message": "feat(agents): add new feature",
        }
    )
    return llm


@pytest.fixture
def sample_diff():
    return """diff --git a/backend/main.py b/backend/main.py
index 1234567..abcdefg 100644
--- a/backend/main.py
+++ b/backend/main.py
@@ -1,2 +1,4 @@
 from fastapi import FastAPI
+from backend.routers import split
 app = FastAPI()
+app.include_router(split.router)
diff --git a/backend/routers/split.py b/backend/routers/split.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/backend/routers/split.py
@@ -0,0 +1,7 @@
+from fastapi import APIRouter
+
+router = APIRouter()
+
+@router.post("/split")
+async def split_diff():
+    return {"status": "ok"}
"""


@pytest.fixture
def empty_diff():
    return ""


class TestSplitAgent:

    @pytest.mark.asyncio
    async def test_split_agent_init(self, mock_llm):
        agent = SplitAgent(llm=mock_llm, retriever=None)

        assert agent.name == "split"
        assert agent.llm == mock_llm
        assert agent.graph is not None

    @pytest.mark.asyncio
    async def test_split_agent_run_basic(self, mock_llm, sample_diff):
        agent = SplitAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff, strategy="directory")

        assert "splits" in result
        assert "reasoning" in result
        assert "total_groups" in result
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_split_agent_run_empty_diff(self, mock_llm, empty_diff):
        agent = SplitAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=empty_diff, strategy="directory")

        assert result["splits"] == []
        assert result["total_groups"] == 0

    @pytest.mark.asyncio
    async def test_split_agent_creates_groups(self, mock_llm, sample_diff):
        agent = SplitAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff, strategy="directory")

        assert result["total_groups"] > 0
        for split in result["splits"]:
            assert "group_id" in split
            assert "files" in split
            assert "commit_message" in split

    @pytest.mark.asyncio
    async def test_split_agent_reasoning_tracked(self, mock_llm, sample_diff):
        agent = SplitAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff, strategy="directory")

        assert len(result["reasoning"]) > 0
        assert any("Parsed diff" in r for r in result["reasoning"])

    @pytest.mark.asyncio
    async def test_split_agent_directory_strategy(self, mock_llm, sample_diff):
        agent = SplitAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff, strategy="directory")

        assert result["error"] is None
        assert len(result["splits"]) > 0

    @pytest.mark.asyncio
    async def test_split_agent_conventional_strategy(self, mock_llm, sample_diff):
        agent = SplitAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff, strategy="conventional")

        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_split_agent_hybrid_strategy(self, mock_llm, sample_diff):
        agent = SplitAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff, strategy="hybrid")

        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_split_agent_invalid_strategy_uses_hybrid(
        self, mock_llm, sample_diff
    ):
        agent = SplitAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff, strategy="invalid_strategy")

        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_split_agent_commit_messages_generated(self, mock_llm, sample_diff):
        agent = SplitAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff, strategy="directory")

        for split in result["splits"]:
            assert split["commit_message"] is not None
            assert len(split["commit_message"]) > 0

    @pytest.mark.asyncio
    async def test_split_agent_files_in_splits(self, mock_llm, sample_diff):
        agent = SplitAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff, strategy="directory")

        all_files = []
        for split in result["splits"]:
            assert len(split["files"]) > 0
            all_files.extend(split["files"])

        assert "backend/main.py" in all_files
        assert "backend/routers/split.py" in all_files


class TestSplitAgentState:

    def test_state_structure(self):
        state: SplitAgentState = {
            "diff": "test diff",
            "repo_path": ".",
            "strategy": "hybrid",
            "parsed_diff": None,
            "commit_groups": [],
            "generated_messages": {},
            "splits": [],
            "reasoning": [],
            "error": None,
        }

        assert state["diff"] == "test diff"
        assert state["strategy"] == "hybrid"
        assert state["error"] is None
