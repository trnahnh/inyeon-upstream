from collections.abc import AsyncIterator
from typing import Any

from langgraph.graph import StateGraph, END

from backend.models.events import EventType, StreamEvent
from .base import BaseAgent
from .pr_state import PRAgentState
from .pr_nodes import analyze_branch_node, generate_pr_node, should_continue


class PRAgent(BaseAgent):
    name = "pr"
    description = "Generate pull request descriptions from branch changes"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(PRAgentState)

        async def _analyze(s: PRAgentState) -> dict[str, Any]:
            return await analyze_branch_node(s, self.llm)

        async def _generate(s: PRAgentState) -> dict[str, Any]:
            return await generate_pr_node(s, self.llm)

        async def _handle_error(s: PRAgentState) -> dict[str, Any]:
            return {
                "pr_description": None,
                "reasoning": s["reasoning"] + ["Stopped due to error"],
            }

        graph.add_node("analyze_branch", _analyze)
        graph.add_node("generate_pr", _generate)
        graph.add_node("handle_error", _handle_error)

        graph.set_entry_point("analyze_branch")
        graph.add_conditional_edges(
            "analyze_branch",
            should_continue,
            {"continue": "generate_pr", "error": "handle_error"},
        )
        graph.add_edge("generate_pr", END)
        graph.add_edge("handle_error", END)

        return graph.compile()

    def _initial_state(
        self,
        diff: str = "",
        commits: list[dict[str, str]] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
        repo_path: str = ".",
    ) -> PRAgentState:
        return {
            "diff": diff,
            "commits": commits or [],
            "branch_name": branch_name,
            "base_branch": base_branch,
            "repo_path": repo_path,
            "analysis": None,
            "pr_description": None,
            "reasoning": [],
            "error": None,
        }

    async def run(
        self,
        diff: str = "",
        commits: list[dict[str, str]] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
        repo_path: str = ".",
        **kwargs,
    ) -> dict[str, Any]:
        final_state = await self.graph.ainvoke(
            self._initial_state(diff, commits, branch_name, base_branch, repo_path)
        )

        return {
            "pr_description": final_state.get("pr_description"),
            "reasoning": final_state.get("reasoning", []),
            "error": final_state.get("error"),
        }

    async def run_stream(
        self,
        diff: str = "",
        commits: list[dict[str, str]] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
        repo_path: str = ".",
        **kwargs,
    ) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(event=EventType.AGENT_START, agent=self.name)

        final_state: dict = {}
        prev_reasoning_len = 0

        try:
            async for state_update in self.graph.astream(
                self._initial_state(diff, commits, branch_name, base_branch, repo_path)
            ):
                for node_name, node_output in state_update.items():
                    final_state.update(node_output)
                    yield StreamEvent(
                        event=EventType.NODE_COMPLETE,
                        agent=self.name,
                        node=node_name,
                    )
                    reasoning = final_state.get("reasoning", [])
                    for step in reasoning[prev_reasoning_len:]:
                        yield StreamEvent(
                            event=EventType.REASONING,
                            agent=self.name,
                            data={"step": step},
                        )
                    prev_reasoning_len = len(reasoning)

            yield StreamEvent(
                event=EventType.RESULT,
                agent=self.name,
                data={
                    "pr_description": final_state.get("pr_description"),
                    "reasoning": final_state.get("reasoning", []),
                    "error": final_state.get("error"),
                },
            )
        except Exception as e:
            yield StreamEvent(
                event=EventType.ERROR, agent=self.name, data={"error": str(e)}
            )

        yield StreamEvent(event=EventType.DONE, agent=self.name)
