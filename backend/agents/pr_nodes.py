from typing import Any

from backend.services.llm.base import LLMProvider
from backend.utils.cost import truncate_diff, get_cached, set_cached
from backend.prompts.pr_prompt import build_pr_prompt
from .pr_state import PRAgentState


async def analyze_branch_node(
    state: PRAgentState, llm: LLMProvider
) -> dict[str, Any]:
    """Analyze branch diff and commits to understand scope of changes."""
    truncated = truncate_diff(state["diff"])
    commits_text = "\n".join(
        f"- {c['hash']} {c['subject']}" for c in state["commits"]
    )

    prompt = f"""Analyze these branch changes for a PR description.

BRANCH: {state["branch_name"]} -> {state["base_branch"]}

COMMITS:
{commits_text}

DIFF:
{truncated}

Respond in JSON:
{{
    "scope": "brief description of what this branch does",
    "change_types": ["feat", "fix", "refactor"],
    "key_changes": ["list of significant changes"],
    "has_breaking_changes": false,
    "has_tests": false,
    "affected_areas": ["area1", "area2"]
}}"""

    cached = get_cached(prompt)
    if cached:
        return {
            "analysis": cached,
            "reasoning": state["reasoning"] + ["Used cached analysis"],
        }

    try:
        response = await llm.generate(prompt, json_mode=True)
    except Exception as e:
        return {
            "error": f"Analysis failed: {e}",
            "reasoning": state["reasoning"] + [f"Analysis error: {e}"],
        }

    set_cached(prompt, response)

    return {
        "analysis": response,
        "reasoning": state["reasoning"]
        + [f"Analyzed {len(state['commits'])} commits across branch"],
    }


async def generate_pr_node(
    state: PRAgentState, llm: LLMProvider
) -> dict[str, Any]:
    """Generate the full PR description from analysis."""
    if state.get("error"):
        return {}

    commits_text = "\n".join(
        f"- {c['hash']} {c['subject']}" for c in state["commits"]
    )

    prompt = build_pr_prompt(
        branch_name=state["branch_name"],
        base_branch=state["base_branch"],
        analysis=state.get("analysis") or {},
        commits_text=commits_text,
    )

    try:
        response = await llm.generate(prompt, json_mode=True)
    except Exception as e:
        return {
            "error": f"PR generation failed: {e}",
            "reasoning": state["reasoning"] + [f"Generation error: {e}"],
        }

    return {
        "pr_description": response,
        "reasoning": state["reasoning"] + ["Generated PR description"],
    }


def should_continue(state: PRAgentState) -> str:
    if state.get("error"):
        return "error"
    return "continue"
