from collections.abc import AsyncIterator
from typing import Any

from backend.models.events import EventType, StreamEvent
from backend.services.llm.base import LLMProvider
from backend.rag import CodeRetriever

from .changelog_agent import ChangelogAgent
from .commit_agent import CommitAgent
from .conflict_agent import ConflictAgent
from .pr_agent import PRAgent
from .review_agent import ReviewAgent
from .split_agent import SplitAgent


class AgentOrchestrator:

    def __init__(self, llm: LLMProvider, retriever: CodeRetriever | None = None):
        self.llm = llm
        self.retriever = retriever
        self.agents = {
            "changelog": ChangelogAgent(llm, retriever),
            "commit": CommitAgent(llm, retriever),
            "pr": PRAgent(llm, retriever),
            "resolve": ConflictAgent(llm, retriever),
            "review": ReviewAgent(llm, retriever),
            "split": SplitAgent(llm, retriever),
        }

    async def route(self, task: str, diff: str, repo_path: str = ".") -> dict[str, Any]:
        task = task.lower()

        if task in self.agents:
            agent = self.agents[task]
            return await agent.run(diff=diff, repo_path=repo_path)

        return await self._auto_route(task, diff, repo_path)

    async def _auto_route(self, task: str, diff: str, repo_path: str) -> dict[str, Any]:
        prompt = f"""Given this task, which agent should handle it?

TASK: {task}

Available agents:
- changelog: Generate changelogs from commit history
- commit: Generate commit messages from diffs
- pr: Generate pull request descriptions
- resolve: Resolve merge conflicts
- review: Review code and provide feedback
- split: Split large diffs into atomic commits

Respond with just the agent name."""

        response = await self.llm.generate(prompt, json_mode=False)
        agent_name = response.get("text", "").strip().lower()

        if agent_name in self.agents:
            return await self.agents[agent_name].run(diff=diff, repo_path=repo_path)

        return await self.agents["commit"].run(diff=diff, repo_path=repo_path)

    async def route_stream(
        self, task: str, diff: str, repo_path: str = "."
    ) -> AsyncIterator[StreamEvent]:
        task = task.lower()

        if task in self.agents:
            agent = self.agents[task]
            async for event in agent.run_stream(diff=diff, repo_path=repo_path):
                yield event
            return

        prompt = f"""Given this task, which agent should handle it?

TASK: {task}

Available agents:
- changelog: Generate changelogs from commit history
- commit: Generate commit messages from diffs
- pr: Generate pull request descriptions
- resolve: Resolve merge conflicts
- review: Review code and provide feedback
- split: Split large diffs into atomic commits

Respond with just the agent name."""

        response = await self.llm.generate(prompt, json_mode=False)
        agent_name = response.get("text", "").strip().lower()

        agent = self.agents.get(agent_name, self.agents["commit"])
        async for event in agent.run_stream(diff=diff, repo_path=repo_path):
            yield event

    def list_agents(self) -> list[dict[str, str]]:
        return [
            {"name": agent.name, "description": agent.description}
            for agent in self.agents.values()
        ]
