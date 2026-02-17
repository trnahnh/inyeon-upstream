"""Prompt template for changelog generation."""

import json

SYSTEM_CONTEXT = """You are a technical writer generating changelogs.
Your changelogs are clear, user-facing, and follow Keep a Changelog conventions."""

CHANGELOG_TEMPLATE = """Generate a changelog from these grouped commits.

FROM: {from_ref}
TO: {to_ref}

GROUPED COMMITS:
{grouped_commits}

Respond with a JSON object in this EXACT format:
{{
    "version": "suggested version label or empty string",
    "date": "{date}",
    "sections": {{
        "feat": ["user-facing description of each feature"],
        "fix": ["user-facing description of each fix"],
        "docs": ["description"],
        "refactor": ["description"],
        "test": ["description"],
        "chore": ["description"]
    }},
    "summary": "1-2 sentence high-level summary of this release"
}}

Rules:
- Only include sections that have commits
- Descriptions should be user-facing, not developer jargon
- Summary captures the overall theme
- Respond with valid JSON only"""


def build_changelog_prompt(
    from_ref: str,
    to_ref: str,
    grouped_commits: dict[str, list[dict[str, str]]],
    date: str,
) -> str:
    return (
        f"{SYSTEM_CONTEXT}\n\n"
        f"{CHANGELOG_TEMPLATE.format(
            from_ref=from_ref,
            to_ref=to_ref,
            grouped_commits=json.dumps(grouped_commits, indent=2),
            date=date,
        )}"
    )
