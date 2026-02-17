import re
from typing import Any

from backend.services.llm.base import LLMProvider
from backend.prompts.conflict_prompt import build_conflict_prompt
from .conflict_state import ConflictAgentState

CONFLICT_PATTERN = re.compile(
    r"<<<<<<<[^\n]*\n(.*?)=======\n(.*?)>>>>>>>[^\n]*",
    re.DOTALL,
)
BATCH_CHAR_LIMIT = 5000


async def parse_conflicts_node(
    state: ConflictAgentState, llm: LLMProvider,
) -> dict[str, Any]:
    """Parse conflict markers in each file. No LLM call."""
    conflicts = state["conflicts"]

    if not conflicts:
        return {
            "error": "No conflicts provided",
            "reasoning": state["reasoning"] + ["No conflicts to parse"],
        }

    parsed = []
    for conflict in conflicts:
        content = conflict.get("content", "")
        markers = CONFLICT_PATTERN.findall(content)
        if not markers:
            continue
        parsed.append(conflict)

    if not parsed:
        return {
            "error": "No conflict markers found in provided files",
            "reasoning": state["reasoning"] + ["No conflict markers detected"],
        }

    return {
        "conflicts": parsed,
        "reasoning": state["reasoning"]
        + [f"Parsed {len(parsed)} file(s) with conflict markers"],
    }


async def resolve_conflicts_node(
    state: ConflictAgentState, llm: LLMProvider,
) -> dict[str, Any]:
    """Resolve conflicts using LLM. Batches small files."""
    if state.get("error"):
        return {}

    conflicts = state["conflicts"]
    resolutions: list[dict[str, Any]] = []

    batch: list[dict[str, str]] = []
    batch_size = 0

    for conflict in conflicts:
        content_len = len(conflict.get("content", ""))
        if batch and batch_size + content_len > BATCH_CHAR_LIMIT:
            results = await _resolve_batch(batch, llm)
            resolutions.extend(results)
            batch = []
            batch_size = 0
        batch.append(conflict)
        batch_size += content_len

    if batch:
        results = await _resolve_batch(batch, llm)
        resolutions.extend(results)

    return {
        "resolutions": resolutions,
        "reasoning": state["reasoning"]
        + [f"Resolved {len(resolutions)} conflict(s)"],
    }


async def _resolve_batch(
    batch: list[dict[str, str]], llm: LLMProvider,
) -> list[dict[str, Any]]:
    """Resolve a batch of conflicts. One LLM call per file."""
    results: list[dict[str, Any]] = []
    for conflict in batch:
        prompt = build_conflict_prompt(
            path=conflict["path"],
            content=conflict.get("content", ""),
            ours=conflict.get("ours", ""),
            theirs=conflict.get("theirs", ""),
        )
        try:
            response = await llm.generate(prompt, json_mode=True)
            results.append({
                "path": conflict["path"],
                "resolved_content": response.get("resolved_content", ""),
                "strategy": response.get("strategy", "unknown"),
                "explanation": response.get("explanation", ""),
            })
        except Exception as e:
            results.append({
                "path": conflict["path"],
                "resolved_content": "",
                "strategy": "error",
                "explanation": f"Resolution failed: {e}",
            })
    return results


def should_continue(state: ConflictAgentState) -> str:
    if state.get("error"):
        return "error"
    return "continue"
