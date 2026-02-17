import re
from datetime import datetime, timezone
from typing import Any

from backend.services.llm.base import LLMProvider
from backend.prompts.changelog_prompt import build_changelog_prompt
from .changelog_state import ChangelogAgentState

CONVENTIONAL_TYPES = {"feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore"}
SUBJECT_PATTERN = re.compile(r"^(\w+)(?:\(.+?\))?[!:]")


async def group_commits_node(
    state: ChangelogAgentState, llm: LLMProvider,
) -> dict[str, Any]:
    """Group commits by conventional commit type. No LLM call."""
    commits = state["commits"]

    if not commits:
        return {
            "error": "No commits provided",
            "reasoning": state["reasoning"] + ["No commits to group"],
        }

    grouped: dict[str, list[dict[str, str]]] = {}
    for commit in commits:
        commit_type = _extract_type(commit.get("subject", ""))
        grouped.setdefault(commit_type, []).append(commit)

    return {
        "grouped_commits": grouped,
        "reasoning": state["reasoning"]
        + [f"Grouped {len(commits)} commits into {len(grouped)} type(s)"],
    }


async def generate_changelog_node(
    state: ChangelogAgentState, llm: LLMProvider,
) -> dict[str, Any]:
    """Generate changelog from grouped commits. 1 LLM call."""
    if state.get("error"):
        return {}

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = build_changelog_prompt(
        from_ref=state["from_ref"],
        to_ref=state["to_ref"],
        grouped_commits=state["grouped_commits"],
        date=date,
    )

    try:
        response = await llm.generate(prompt, json_mode=True)
    except Exception as e:
        return {
            "error": f"Changelog generation failed: {e}",
            "reasoning": state["reasoning"] + [f"Generation error: {e}"],
        }

    return {
        "changelog": response,
        "reasoning": state["reasoning"] + ["Generated changelog"],
    }


def should_continue(state: ChangelogAgentState) -> str:
    if state.get("error"):
        return "error"
    return "continue"


def _extract_type(subject: str) -> str:
    """Extract conventional commit type from subject line."""
    match = SUBJECT_PATTERN.match(subject)
    if match:
        commit_type = match.group(1).lower()
        if commit_type in CONVENTIONAL_TYPES:
            return commit_type
    return "chore"
