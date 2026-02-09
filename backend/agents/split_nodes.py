from typing import Any

from backend.diff import DiffParser
from backend.clustering import (
    ClusteringStrategy,
    DirectoryStrategy,
    SemanticStrategy,
    ConventionalStrategy,
    HybridStrategy,
)
from backend.services.llm.base import LLMProvider
from backend.rag.embeddings import EmbeddingService
from .split_state import SplitAgentState


async def parse_diff_node(state: SplitAgentState) -> dict[str, Any]:
    parser = DiffParser()
    try:
        parsed = parser.parse(state["diff"])
        return {
            "parsed_diff": parsed,
            "reasoning": state["reasoning"]
            + [
                f"Parsed diff: {len(parsed.files)} files, "
                f"+{parsed.total_added}/-{parsed.total_removed} lines"
            ],
        }
    except Exception as e:
        return {
            "error": f"Failed to parse diff: {e}",
            "reasoning": state["reasoning"] + [f"Parse error: {e}"],
        }


async def cluster_hunks_node(
    state: SplitAgentState,
    llm: LLMProvider,
    embedding_service: EmbeddingService | None = None,
) -> dict[str, Any]:
    if state.get("error"):
        return {}

    strategy = _get_strategy(state["strategy"], llm, embedding_service)

    try:
        groups = await strategy.cluster(state["parsed_diff"])
        return {
            "commit_groups": groups,
            "reasoning": state["reasoning"]
            + [f"Created {len(groups)} commit groups using '{strategy.name}' strategy"],
        }
    except Exception as e:
        return {
            "error": f"Clustering failed: {e}",
            "reasoning": state["reasoning"] + [f"Cluster error: {e}"],
        }


async def generate_messages_node(
    state: SplitAgentState,
    llm: LLMProvider,
) -> dict[str, Any]:
    if state.get("error"):
        return {}

    messages = {}
    splits = []

    for group in state["commit_groups"]:
        files_summary = "\n".join(f"- {f}" for f in group.files)

        prompt = f"""Generate a conventional commit message for these changes.

FILES:
{files_summary}

SUGGESTED TYPE: {group.suggested_type or 'auto-detect'}
SCOPE: {group.suggested_scope or 'auto-detect'}

Respond in JSON:
{{
    "type": "feat|fix|refactor|docs|test|chore|style|perf",
    "scope": "optional scope or null",
    "subject": "imperative description under 50 chars",
    "message": "full formatted commit message"
}}"""

        response = await llm.generate(prompt, json_mode=True)
        message = response.get(
            "message", f"{group.suggested_type or 'chore'}: update {group.files[0]}"
        )
        commit_type = response.get("type", group.suggested_type)

        messages[group.id] = message
        splits.append(
            {
                "group_id": group.id,
                "files": group.files,
                "hunk_count": len(group.hunks),
                "commit_message": message,
                "commit_type": commit_type,
                "scope": response.get("scope", group.suggested_scope),
            }
        )

    return {
        "generated_messages": messages,
        "splits": splits,
        "reasoning": state["reasoning"] + [f"Generated {len(splits)} commit messages"],
    }


def should_continue(state: SplitAgentState) -> str:
    if state.get("error"):
        return "error"
    return "continue"


def _get_strategy(
    name: str,
    llm: LLMProvider,
    embedding_service: EmbeddingService | None,
) -> ClusteringStrategy:
    strategies: dict[str, ClusteringStrategy] = {
        "directory": DirectoryStrategy(),
        "conventional": ConventionalStrategy(llm),
        "hybrid": HybridStrategy(llm, embedding_service),
    }

    if embedding_service:
        strategies["semantic"] = SemanticStrategy(embedding_service)

    return strategies.get(name, strategies["hybrid"])
