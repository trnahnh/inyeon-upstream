from typing import Any

from langgraph.graph import StateGraph, END

from .base import BaseAgent
from .state import AgentState
from .nodes import search_rag_context


class ReviewAgent(BaseAgent):
    """Agent that reviews code and provides feedback."""

    name = "review"
    description = "Review code changes and provide quality feedback"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Construct the LangGraph state machine."""
        graph = StateGraph(AgentState)

        async def _search_rag(s: AgentState) -> dict[str, Any]:
            return await search_rag_context(s, self.retriever)

        async def _review(s: AgentState) -> dict[str, Any]:
            return await self._review_code(s)

        graph.add_node("search_rag", _search_rag)
        graph.add_node("review", _review)

        graph.set_entry_point("search_rag" if self.retriever else "review")

        if self.retriever:
            graph.add_edge("search_rag", "review")

        graph.add_edge("review", END)

        return graph.compile()

    async def _review_code(self, state: AgentState) -> dict[str, Any]:
        """Review the diff and provide feedback."""
        rag_context = ""
        if state.get("rag_context"):
            rag_context = "\n\nRELEVANT CODE FROM CODEBASE:\n"
            for item in state["rag_context"]:
                rag_context += f"\n--- {item['path']} ---\n{item['content'][:500]}\n"

        prompt = f"""You are a senior code reviewer. Review this diff and provide constructive feedback.

DIFF:
{state["diff"]}
{rag_context}

Respond in JSON:
{{
    "summary": "Brief summary of changes",
    "quality_score": 1-10,
    "issues": [
        {{"severity": "high|medium|low", "description": "issue description", "suggestion": "how to fix"}}
    ],
    "positives": ["good things about the code"],
    "suggestions": ["general improvement suggestions"]
}}

Focus on:
- Code quality and readability
- Potential bugs or edge cases
- Security concerns
- Performance issues
- Best practices"""

        response = await self.llm.generate(prompt, json_mode=True)

        return {
            "review": response,
            "reasoning": state["reasoning"] + ["Completed code review"],
        }

    async def run(self, diff: str, repo_path: str = ".") -> dict[str, Any]:
        """Run the review agent on a diff."""
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
            "review": final_state.get("review"),
            "reasoning": final_state.get("reasoning", []),
            "rag_context": final_state.get("rag_context", []),
        }
