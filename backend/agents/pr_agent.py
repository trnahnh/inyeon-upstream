from typing import Any

from langgraph.graph import StateGraph, END

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

    async def run(
        self,
        diff: str = "",
        commits: list[dict[str, str]] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
        repo_path: str = ".",
        **kwargs,
    ) -> dict[str, Any]:
        initial_state: PRAgentState = {
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

        final_state = await self.graph.ainvoke(initial_state)

        return {
            "pr_description": final_state.get("pr_description"),
            "reasoning": final_state.get("reasoning", []),
            "error": final_state.get("error"),
        }
