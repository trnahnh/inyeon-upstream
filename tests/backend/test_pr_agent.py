import pytest
from unittest.mock import AsyncMock

from backend.agents.pr_agent import PRAgent
from backend.utils.cost import clear_cache


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value={
            "title": "feat(auth): add session management",
            "summary": "Adds session timeout and refresh.",
            "changes": ["- Add session timeout", "- Add refresh token"],
            "testing": "Run auth tests",
            "breaking_changes": [],
        }
    )
    return llm


@pytest.fixture
def sample_diff():
    return """diff --git a/auth.py b/auth.py
index 1234567..abcdefg 100644
--- a/auth.py
+++ b/auth.py
@@ -1,3 +1,5 @@
 def login(user):
+    session = create_session(user)
+    return session
     pass
"""


@pytest.fixture
def sample_commits():
    return [
        {"hash": "abc12345", "subject": "feat(auth): add session creation", "body": "", "author": "dev"},
        {"hash": "def67890", "subject": "test(auth): add session tests", "body": "", "author": "dev"},
    ]


class TestPRAgent:

    def setup_method(self):
        clear_cache()

    @pytest.mark.asyncio
    async def test_pr_agent_init(self, mock_llm):
        agent = PRAgent(llm=mock_llm, retriever=None)
        assert agent.name == "pr"
        assert agent.graph is not None

    @pytest.mark.asyncio
    async def test_pr_agent_run_basic(self, mock_llm, sample_diff):
        agent = PRAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff)

        assert "pr_description" in result
        assert "reasoning" in result
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_pr_agent_run_with_commits(self, mock_llm, sample_diff, sample_commits):
        agent = PRAgent(llm=mock_llm, retriever=None)
        result = await agent.run(
            diff=sample_diff,
            commits=sample_commits,
            branch_name="feature/auth",
            base_branch="main",
        )

        assert result["pr_description"] is not None
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_pr_agent_reasoning_tracked(self, mock_llm, sample_diff, sample_commits):
        agent = PRAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff, commits=sample_commits)

        assert len(result["reasoning"]) >= 2

    @pytest.mark.asyncio
    async def test_pr_agent_handles_llm_error(self, mock_llm, sample_diff):
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM down"))
        agent = PRAgent(llm=mock_llm, retriever=None)
        result = await agent.run(diff=sample_diff)

        assert result["error"] is not None
        assert "Analysis failed" in result["error"]
