import pytest
from unittest.mock import AsyncMock

from backend.agents.conflict_agent import ConflictAgent
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
            "resolved_content": 'def greet():\n    print("Hello from both")\n',
            "strategy": "merge",
            "explanation": "Combined both greeting messages",
        }
    )
    return llm


@pytest.fixture
def sample_conflicts():
    return [
        {
            "path": "greet.py",
            "content": CONFLICT_CONTENT,
            "ours": 'def greet():\n    print("Hello from ours")\n',
            "theirs": 'def greet():\n    print("Hello from theirs")\n',
        },
    ]


class TestConflictAgent:

    def setup_method(self):
        clear_cache()

    @pytest.mark.asyncio
    async def test_conflict_agent_init(self, mock_llm):
        agent = ConflictAgent(llm=mock_llm, retriever=None)
        assert agent.name == "resolve"
        assert agent.graph is not None

    @pytest.mark.asyncio
    async def test_conflict_agent_run(self, mock_llm, sample_conflicts):
        agent = ConflictAgent(llm=mock_llm, retriever=None)
        result = await agent.run(conflicts=sample_conflicts)

        assert "resolutions" in result
        assert "reasoning" in result
        assert result["error"] is None
        assert len(result["resolutions"]) == 1

    @pytest.mark.asyncio
    async def test_conflict_agent_resolution_content(self, mock_llm, sample_conflicts):
        agent = ConflictAgent(llm=mock_llm, retriever=None)
        result = await agent.run(conflicts=sample_conflicts)

        res = result["resolutions"][0]
        assert res["path"] == "greet.py"
        assert res["strategy"] == "merge"
        assert res["resolved_content"] != ""

    @pytest.mark.asyncio
    async def test_conflict_agent_empty_conflicts(self, mock_llm):
        agent = ConflictAgent(llm=mock_llm, retriever=None)
        result = await agent.run(conflicts=[])

        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_conflict_agent_reasoning_tracked(self, mock_llm, sample_conflicts):
        agent = ConflictAgent(llm=mock_llm, retriever=None)
        result = await agent.run(conflicts=sample_conflicts)

        assert len(result["reasoning"]) >= 2

    @pytest.mark.asyncio
    async def test_conflict_agent_handles_llm_error(self, mock_llm, sample_conflicts):
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM down"))
        agent = ConflictAgent(llm=mock_llm, retriever=None)
        result = await agent.run(conflicts=sample_conflicts)

        assert len(result["resolutions"]) == 1
        assert result["resolutions"][0]["strategy"] == "error"
