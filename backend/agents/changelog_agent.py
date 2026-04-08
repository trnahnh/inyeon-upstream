from collections.abc import AsyncIterator
from typing import Any

from langgraph.graph import StateGraph, END

from backend.models.events import EventType, StreamEvent
from .base import BaseAgent
from .changelog_state import ChangelogAgentState
from .changelog_nodes import group_commits_node, generate_changelog_node, should_continue


class ChangelogAgent(BaseAgent):
    name = "changelog"
    description = "Generate changelogs from commit history"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(ChangelogAgentState)

        async def _group(s: ChangelogAgentState) -> dict[str, Any]:
            return await group_commits_node(s, self.llm)

        async def _generate(s: ChangelogAgentState) -> dict[str, Any]:
            return await generate_changelog_node(s, self.llm)

        async def _handle_error(s: ChangelogAgentState) -> dict[str, Any]:
            return {
                "changelog": None,
                "reasoning": s["reasoning"] + ["Stopped due to error"],
            }

        graph.add_node("group_commits", _group)
        graph.add_node("generate_changelog", _generate)
        graph.add_node("handle_error", _handle_error)

        graph.set_entry_point("group_commits")
        graph.add_conditional_edges(
            "group_commits",
            should_continue,
            {"continue": "generate_changelog", "error": "handle_error"},
        )
        graph.add_edge("generate_changelog", END)
        graph.add_edge("handle_error", END)

        return graph.compile()

    def _initial_state(
        self,
        commits: list[dict[str, str]] | None = None,
        from_ref: str = "",
        to_ref: str = "HEAD",
        repo_path: str = ".",
    ) -> ChangelogAgentState:
        return {
            "commits": commits or [],
            "from_ref": from_ref,
            "to_ref": to_ref,
            "repo_path": repo_path,
            "grouped_commits": {},
            "changelog": None,
            "reasoning": [],
            "error": None,
        }

    async def run(
        self,
        commits: list[dict[str, str]] | None = None,
        from_ref: str = "",
        to_ref: str = "HEAD",
        repo_path: str = ".",
        **kwargs,
    ) -> dict[str, Any]:
        final_state = await self.graph.ainvoke(
            self._initial_state(commits, from_ref, to_ref, repo_path)
        )

        return {
            "changelog": final_state.get("changelog"),
            "reasoning": final_state.get("reasoning", []),
            "error": final_state.get("error"),
        }

    async def run_stream(
        self,
        commits: list[dict[str, str]] | None = None,
        from_ref: str = "",
        to_ref: str = "HEAD",
        repo_path: str = ".",
        **kwargs,
    ) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(event=EventType.AGENT_START, agent=self.name)

        final_state: dict = {}
        prev_reasoning_len = 0

        try:
            async for state_update in self.graph.astream(
                self._initial_state(commits, from_ref, to_ref, repo_path)
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
                    "changelog": final_state.get("changelog"),
                    "reasoning": final_state.get("reasoning", []),
                    "error": final_state.get("error"),
                },
            )
        except Exception as e:
            yield StreamEvent(
                event=EventType.ERROR, agent=self.name, data={"error": str(e)}
            )

        yield StreamEvent(event=EventType.DONE, agent=self.name)
