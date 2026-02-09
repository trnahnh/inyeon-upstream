from typing import Any

from langgraph.graph import StateGraph, END

from .base import BaseAgent
from .split_state import SplitAgentState
from .split_nodes import (
    parse_diff_node,
    cluster_hunks_node,
    generate_messages_node,
    should_continue,
)


class SplitAgent(BaseAgent):

    name = "split"
    description = "Split large diffs into smaller, atomic commits"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(SplitAgentState)

        async def _parse(s: SplitAgentState) -> dict[str, Any]:
            return await parse_diff_node(s)

        async def _cluster(s: SplitAgentState) -> dict[str, Any]:
            return await cluster_hunks_node(s, self.llm, self.retriever)

        async def _generate(s: SplitAgentState) -> dict[str, Any]:
            return await generate_messages_node(s, self.llm)

        async def _handle_error(s: SplitAgentState) -> dict[str, Any]:
            return {
                "splits": [],
                "reasoning": s["reasoning"] + ["Stopped due to error"],
            }

        graph.add_node("parse_diff", _parse)
        graph.add_node("cluster_hunks", _cluster)
        graph.add_node("generate_messages", _generate)
        graph.add_node("handle_error", _handle_error)

        graph.set_entry_point("parse_diff")

        graph.add_conditional_edges(
            "parse_diff",
            should_continue,
            {"continue": "cluster_hunks", "error": "handle_error"},
        )
        graph.add_conditional_edges(
            "cluster_hunks",
            should_continue,
            {"continue": "generate_messages", "error": "handle_error"},
        )
        graph.add_edge("generate_messages", END)
        graph.add_edge("handle_error", END)

        return graph.compile()

    async def run(
        self,
        diff: str,
        repo_path: str = ".",
        strategy: str = "hybrid",
    ) -> dict[str, Any]:
        initial_state: SplitAgentState = {
            "diff": diff,
            "repo_path": repo_path,
            "strategy": strategy,
            "parsed_diff": None,
            "commit_groups": [],
            "generated_messages": {},
            "splits": [],
            "reasoning": [],
            "error": None,
        }

        final_state = await self.graph.ainvoke(initial_state)

        return {
            "splits": final_state.get("splits", []),
            "reasoning": final_state.get("reasoning", []),
            "error": final_state.get("error"),
            "total_groups": len(final_state.get("splits", [])),
        }
