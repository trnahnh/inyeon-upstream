from typing import Any, TypedDict


class ConflictAgentState(TypedDict):
    conflicts: list[dict[str, str]]
    repo_path: str
    resolutions: list[dict[str, Any]]
    reasoning: list[str]
    error: str | None
