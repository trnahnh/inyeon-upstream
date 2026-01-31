from typing import Any

from langgraph.graph import StateGraph, END

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

    async def run(self, diff: str, repo_path: str = ".") -> dict[str, Any]:
        """Run the agent on a diff."""
        initial_state: AgentState = {
            "diff": diff,
            "repo_path": repo_path,
            "analysis": None,
            "needs_context": False,
            "files_to_read": [],
            "file_contents": {},
            "rag_context": [],
            "commit_message": None,
            "reasoning": [],
        }

        final_state = await self.graph.ainvoke(initial_state)

        return {
            "commit_message": final_state.get("commit_message"),
            "reasoning": final_state.get("reasoning", []),
            "analysis": final_state.get("analysis"),
            "rag_context": final_state.get("rag_context", []),
        }
