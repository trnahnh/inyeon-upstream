"""Prompt template for merge conflict resolution."""

SYSTEM_CONTEXT = """You are a senior engineer resolving merge conflicts.
You understand both sides of the conflict and produce correct, compilable merged code."""

CONFLICT_TEMPLATE = """Resolve the merge conflicts in the following file.

FILE: {path}

OUR VERSION (current branch):
```
{ours}
```

THEIR VERSION (incoming branch):
```
{theirs}
```

CONFLICTED CONTENT:
```
{content}
```

Respond with a JSON object in this EXACT format:
{{
    "resolved_content": "the full resolved file content",
    "strategy": "one of: ours, theirs, merge, rewrite",
    "explanation": "brief explanation of how you resolved the conflict"
}}

Rules:
- resolved_content must be the COMPLETE file, not just the conflicted section
- Remove ALL conflict markers (<<<<<<<, =======, >>>>>>>)
- strategy describes your approach: ours (kept our changes), theirs (kept their changes), merge (combined both), rewrite (rewrote the section)
- Respond with valid JSON only"""


def build_conflict_prompt(
    path: str,
    content: str,
    ours: str,
    theirs: str,
) -> str:
    return (
        f"{SYSTEM_CONTEXT}\n\n"
        f"{CONFLICT_TEMPLATE.format(
            path=path,
            content=content,
            ours=ours,
            theirs=theirs,
        )}"
    )
