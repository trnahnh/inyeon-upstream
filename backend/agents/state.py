from typing import Any, TypedDict


class AgentState(TypedDict):
    # --- Input ---
    diff: str
    """The git diff to analyze."""

    repo_path: str
    """Path to the repository root."""

    # --- Analysis Phase ---
    analysis: dict[str, Any] | None
    """Output from analyze node."""

    needs_context: bool
    """Whether agent needs additional context."""

    files_to_read: list[str]
    """File paths to read for context."""

    # --- Context Phase ---
    file_contents: dict[str, str]
    """Contents of files read. Format: {path: content}."""

    rag_context: list[dict[str, Any]]
    """Relevant code found via RAG search."""

    # --- Output ---
    commit_message: str | None
    """Final generated commit message."""

    review: dict[str, Any] | None
    """Code review feedback."""

    reasoning: list[str]
    """Agent's reasoning steps."""
