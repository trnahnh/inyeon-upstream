from typing import Any

from backend.services.llm.base import LLMProvider
from backend.rag import CodeRetriever

from .commit_agent import CommitAgent
from .review_agent import ReviewAgent
from .split_agent import SplitAgent


class AgentOrchestrator:
    """Routes requests to specialized agents."""

    def __init__(self, llm: LLMProvider, retriever: CodeRetriever | None = None):
        self.llm = llm
        self.retriever = retriever
        self.agents = {
            "commit": CommitAgent(llm, retriever),
            "review": ReviewAgent(llm, retriever),
            "split": SplitAgent(llm, retriever),
        }

    async def route(self, task: str, diff: str, repo_path: str = ".") -> dict[str, Any]:
        """Route to appropriate agent based on task."""
        task = task.lower()

        if task in self.agents:
            agent = self.agents[task]
            return await agent.run(diff=diff, repo_path=repo_path)

        return await self._auto_route(task, diff, repo_path)

    async def _auto_route(self, task: str, diff: str, repo_path: str) -> dict[str, Any]:
        """Use LLM to determine which agent to use."""
        prompt = f"""Given this task, which agent should handle it?

TASK: {task}

Available agents:
- commit: Generate commit messages from diffs
- review: Review code and provide feedback

Respond with just the agent name: commit or review"""

        response = await self.llm.generate(prompt, json_mode=False)
        agent_name = response.get("text", "").strip().lower()

        if agent_name in self.agents:
            return await self.agents[agent_name].run(diff=diff, repo_path=repo_path)

        # Default to commit agent
        return await self.agents["commit"].run(diff=diff, repo_path=repo_path)

    def list_agents(self) -> list[dict[str, str]]:
        """List available agents."""
        return [
            {"name": agent.name, "description": agent.description}
            for agent in self.agents.values()
        ]
