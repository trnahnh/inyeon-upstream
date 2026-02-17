"""Prompt template for pull request description generation."""

import json

SYSTEM_CONTEXT = """You are a senior engineer writing pull request descriptions.
Your PR descriptions are clear, thorough, and help reviewers understand changes quickly."""

PR_TEMPLATE = """Generate a pull request description for these branch changes.

BRANCH: {branch_name} -> {base_branch}

ANALYSIS:
{analysis}

COMMITS:
{commits_text}

Respond with a JSON object in this EXACT format:
{{
    "title": "concise PR title under 70 chars, conventional format: type(scope): description",
    "summary": "2-3 sentence overview of what and why",
    "changes": ["- Change description 1", "- Change description 2"],
    "testing": "How to test these changes",
    "breaking_changes": []
}}

Rules:
- Title uses conventional format: type(scope): description
- Summary explains WHAT and WHY at a high level
- Changes is a detailed list organized by area
- Testing gives concrete steps a reviewer can follow
- breaking_changes is an empty array if none
- Respond with valid JSON only"""


def build_pr_prompt(
    branch_name: str,
    base_branch: str,
    analysis: dict,
    commits_text: str,
) -> str:
    return (
        f"{SYSTEM_CONTEXT}\n\n"
        f"{PR_TEMPLATE.format(
            branch_name=branch_name,
            base_branch=base_branch,
            analysis=json.dumps(analysis, indent=2),
            commits_text=commits_text,
        )}"
    )
