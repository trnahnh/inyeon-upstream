from typing import Any, TypedDict


class ChangelogAgentState(TypedDict):
    commits: list[dict[str, str]]
    from_ref: str
    to_ref: str
    repo_path: str
    grouped_commits: dict[str, list[dict[str, str]]]
    changelog: dict[str, Any] | None
    reasoning: list[str]
    error: str | None
