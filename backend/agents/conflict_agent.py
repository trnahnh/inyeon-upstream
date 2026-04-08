from collections.abc import AsyncIterator
from typing import Any

from langgraph.graph import StateGraph, END

from backend.models.events import EventType, StreamEvent
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

    def _initial_state(
        self, conflicts: list[dict[str, str]] | None = None, repo_path: str = "."
    ) -> ConflictAgentState:
        return {
            "conflicts": conflicts or [],
            "repo_path": repo_path,
            "resolutions": [],
            "reasoning": [],
            "error": None,
        }

    async def run(
        self,
        conflicts: list[dict[str, str]] | None = None,
        repo_path: str = ".",
        **kwargs,
    ) -> dict[str, Any]:
        final_state = await self.graph.ainvoke(
            self._initial_state(conflicts, repo_path)
        )

        return {
            "resolutions": final_state.get("resolutions", []),
            "reasoning": final_state.get("reasoning", []),
            "error": final_state.get("error"),
        }

    async def run_stream(
        self,
        conflicts: list[dict[str, str]] | None = None,
        repo_path: str = ".",
        **kwargs,
    ) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(event=EventType.AGENT_START, agent=self.name)

        final_state: dict = {}
        prev_reasoning_len = 0

        try:
            async for state_update in self.graph.astream(
                self._initial_state(conflicts, repo_path)
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
                    "resolutions": final_state.get("resolutions", []),
                    "reasoning": final_state.get("reasoning", []),
                    "error": final_state.get("error"),
                },
            )
        except Exception as e:
            yield StreamEvent(
                event=EventType.ERROR, agent=self.name, data={"error": str(e)}
            )

        yield StreamEvent(event=EventType.DONE, agent=self.name)
