from collections.abc import AsyncIterator
from typing import Any

from langgraph.graph import StateGraph, END

from backend.models.events import EventType, StreamEvent
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
            embedding_svc = self.retriever.embeddings if self.retriever else None
            return await cluster_hunks_node(s, self.llm, embedding_svc)

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

    def _initial_state(
        self, diff: str, repo_path: str = ".", strategy: str = "hybrid"
    ) -> SplitAgentState:
        return {
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

    async def run(
        self,
        diff: str,
        repo_path: str = ".",
        strategy: str = "hybrid",
    ) -> dict[str, Any]:
        final_state = await self.graph.ainvoke(
            self._initial_state(diff, repo_path, strategy)
        )

        return {
            "splits": final_state.get("splits", []),
            "reasoning": final_state.get("reasoning", []),
            "error": final_state.get("error"),
            "total_groups": len(final_state.get("splits", [])),
        }

    async def run_stream(
        self, diff: str, repo_path: str = ".", strategy: str = "hybrid", **kwargs
    ) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(event=EventType.AGENT_START, agent=self.name)

        final_state: dict = {}
        prev_reasoning_len = 0

        try:
            async for state_update in self.graph.astream(
                self._initial_state(diff, repo_path, strategy)
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

            splits = final_state.get("splits", [])
            yield StreamEvent(
                event=EventType.RESULT,
                agent=self.name,
                data={
                    "splits": splits,
                    "reasoning": final_state.get("reasoning", []),
                    "error": final_state.get("error"),
                    "total_groups": len(splits),
                },
            )
        except Exception as e:
            yield StreamEvent(
                event=EventType.ERROR, agent=self.name, data={"error": str(e)}
            )

        yield StreamEvent(event=EventType.DONE, agent=self.name)
