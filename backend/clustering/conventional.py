import json

from backend.diff import ParsedDiff, ParsedFile
from backend.services.llm.base import LLMProvider
from .base import ClusteringStrategy
from .models import CommitGroup, HunkReference


COMMIT_TYPES = ["feat", "fix", "refactor", "test", "docs", "style", "chore", "perf"]


class ConventionalStrategy(ClusteringStrategy):

    name = "conventional"
    description = "Group by commit type (feat, fix, test, docs, etc.)"

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def cluster(self, parsed_diff: ParsedDiff) -> list[CommitGroup]:
        if not parsed_diff.files:
            return []

        classifications = await self._classify_files(parsed_diff.files)

        groups: dict[str, CommitGroup] = {}
        for file in parsed_diff.files:
            commit_type = classifications.get(file.path, "chore")

            if commit_type not in groups:
                groups[commit_type] = CommitGroup(
                    id=f"conv-{commit_type}",
                    hunks=[],
                    files=[],
                    suggested_type=commit_type,
                    reasoning=f"Changes classified as '{commit_type}'",
                )

            groups[commit_type].files.append(file.path)
            for hunk in file.hunks:
                groups[commit_type].hunks.append(
                    HunkReference(file_path=file.path, hunk_id=hunk.id)
                )

        return list(groups.values())

    async def _classify_files(self, files: list[ParsedFile]) -> dict[str, str]:
        """Classify all files in a single LLM call to avoid per-file rate limit hits."""
        file_entries = []
        for file in files:
            preview = file.hunks[0].content[:300] if file.hunks else ""
            file_entries.append(
                f'- path: "{file.path}", change_type: "{file.change_type.value}", preview: {json.dumps(preview[:200])}'
            )

        prompt = f"""Classify each file change into ONE conventional commit type.

FILES:
{chr(10).join(file_entries)}

Available types: {", ".join(COMMIT_TYPES)}

Respond with a JSON object mapping each file path to its type.
Example: {{"src/app.py": "feat", "tests/test_app.py": "test"}}
Output ONLY valid JSON, nothing else."""

        try:
            response = await self.llm.generate(prompt, json_mode=True)
            if isinstance(response, dict):
                return {
                    path: (v if v in COMMIT_TYPES else "chore")
                    for path, v in response.items()
                }
        except Exception:
            pass

        # Fallback: everything is chore
        return {f.path: "chore" for f in files}
