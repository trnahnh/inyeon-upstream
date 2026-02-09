from typing import Any, TypedDict

from backend.diff import ParsedDiff
from backend.clustering import CommitGroup


class SplitAgentState(TypedDict):
    diff: str
    repo_path: str
    strategy: str

    parsed_diff: ParsedDiff | None
    commit_groups: list[CommitGroup]
    generated_messages: dict[str, str]

    splits: list[dict[str, Any]]
    reasoning: list[str]
    error: str | None
