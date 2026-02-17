from typing import Any

from langgraph.graph import StateGraph, END

from .base import BaseAgent
from .conflict_state import ConflictAgentState
from .conflict_nodes import parse_conflicts_node, resolve_conflicts_node, should_continue


class ConflictAgent(BaseAgent):
    name = "resolve"
    description = "Resolve merge conflicts using AI analysis"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(ConflictAgentState)

        async def _parse(s: ConflictAgentState) -> dict[str, Any]:
            return await parse_conflicts_node(s, self.llm)

        async def _resolve(s: ConflictAgentState) -> dict[str, Any]:
            return await resolve_conflicts_node(s, self.llm)

        async def _handle_error(s: ConflictAgentState) -> dict[str, Any]:
            return {
                "resolutions": [],
                "reasoning": s["reasoning"] + ["Stopped due to error"],
            }

        graph.add_node("parse_conflicts", _parse)
        graph.add_node("resolve_conflicts", _resolve)
        graph.add_node("handle_error", _handle_error)

        graph.set_entry_point("parse_conflicts")
        graph.add_conditional_edges(
            "parse_conflicts",
            should_continue,
            {"continue": "resolve_conflicts", "error": "handle_error"},
        )
        graph.add_edge("resolve_conflicts", END)
        graph.add_edge("handle_error", END)

        return graph.compile()

    async def run(
        self,
        conflicts: list[dict[str, str]] | None = None,
        repo_path: str = ".",
        **kwargs,
    ) -> dict[str, Any]:
        initial_state: ConflictAgentState = {
            "conflicts": conflicts or [],
            "repo_path": repo_path,
            "resolutions": [],
            "reasoning": [],
            "error": None,
        }

        final_state = await self.graph.ainvoke(initial_state)

        return {
            "resolutions": final_state.get("resolutions", []),
            "reasoning": final_state.get("reasoning", []),
            "error": final_state.get("error"),
        }
