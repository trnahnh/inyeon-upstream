from collections.abc import AsyncIterator
from typing import Any

from langgraph.graph import StateGraph, END

from backend.models.events import EventType, StreamEvent
from .base import BaseAgent
from .state import AgentState
from .nodes import (
    analyze_diff,
    gather_context,
    generate_commit,
    should_gather_context,
    search_rag_context,
)


class CommitAgent(BaseAgent):
    """Agent that generates commit messages from diffs."""

    name = "commit"
    description = "Generate conventional commit messages from git diffs"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Construct the LangGraph state machine."""
        graph = StateGraph(AgentState)

        async def _analyze(s: AgentState) -> dict[str, Any]:
            return await analyze_diff(s, self.llm)

        async def _search_rag(s: AgentState) -> dict[str, Any]:
            return await search_rag_context(s, self.retriever)

        async def _gather(s: AgentState) -> dict[str, Any]:
            return await gather_context(s, self.llm)

        async def _generate(s: AgentState) -> dict[str, Any]:
            return await generate_commit(s, self.llm)

        graph.add_node("analyze", _analyze)
        graph.add_node("search_rag", _search_rag)
        graph.add_node("gather_context", _gather)
        graph.add_node("generate_commit", _generate)

        graph.set_entry_point("analyze")

        if self.retriever:
            graph.add_edge("analyze", "search_rag")
            graph.add_conditional_edges(
                "search_rag",
                should_gather_context,
                {
                    "gather_context": "gather_context",
                    "generate_commit": "generate_commit",
                },
            )
        else:
            graph.add_conditional_edges(
                "analyze",
                should_gather_context,
                {
                    "gather_context": "gather_context",
                    "generate_commit": "generate_commit",
                },
            )

        graph.add_edge("gather_context", "generate_commit")
        graph.add_edge("generate_commit", END)

        return graph.compile()

    def _initial_state(self, diff: str, repo_path: str = ".") -> AgentState:
        return {
            "diff": diff,
            "repo_path": repo_path,
            "analysis": None,
            "needs_context": False,
            "files_to_read": [],
            "file_contents": {},
            "rag_context": [],
            "commit_message": None,
            "review": None,
            "reasoning": [],
        }

    async def run(self, diff: str, repo_path: str = ".") -> dict[str, Any]:
        """Run the agent on a diff."""
        final_state = await self.graph.ainvoke(self._initial_state(diff, repo_path))

        return {
            "commit_message": final_state.get("commit_message"),
            "reasoning": final_state.get("reasoning", []),
            "analysis": final_state.get("analysis"),
            "rag_context": final_state.get("rag_context", []),
        }

    async def run_stream(
        self, diff: str, repo_path: str = ".", **kwargs
    ) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(event=EventType.AGENT_START, agent=self.name)

        final_state = self._initial_state(diff, repo_path)
        prev_reasoning_len = 0

        try:
            async for state_update in self.graph.astream(
                self._initial_state(diff, repo_path)
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
                    "commit_message": final_state.get("commit_message"),
                    "reasoning": final_state.get("reasoning", []),
                    "analysis": final_state.get("analysis"),
                    "rag_context": final_state.get("rag_context", []),
                },
            )
        except Exception as e:
            yield StreamEvent(
                event=EventType.ERROR, agent=self.name, data={"error": str(e)}
            )

        yield StreamEvent(event=EventType.DONE, agent=self.name)
