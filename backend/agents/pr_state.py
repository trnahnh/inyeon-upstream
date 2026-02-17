from typing import Any, TypedDict


class PRAgentState(TypedDict):
    diff: str
    commits: list[dict[str, str]]
    branch_name: str
    base_branch: str
    repo_path: str

    analysis: dict[str, Any] | None

    pr_description: dict[str, Any] | None
    reasoning: list[str]
    error: str | None
