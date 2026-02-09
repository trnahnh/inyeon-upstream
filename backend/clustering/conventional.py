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
        classifications: dict[str, str] = {}

        for file in parsed_diff.files:
            commit_type = await self._classify_file(file)
            classifications[file.path] = commit_type

        groups: dict[str, CommitGroup] = {}
        for file in parsed_diff.files:
            commit_type = classifications[file.path]

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

    async def _classify_file(self, file: ParsedFile) -> str:
        hunk_preview = ""
        if file.hunks:
            hunk_preview = file.hunks[0].content[:500]

        prompt = f"""Classify this file change into ONE conventional commit type.

FILE: {file.path}
CHANGE TYPE: {file.change_type.value}
PREVIEW:
{hunk_preview}

Available types: {', '.join(COMMIT_TYPES)}

Respond with ONLY the type name (e.g., "feat" or "fix"), nothing else."""

        response = await self.llm.generate(prompt)
        result = response.get("text", "chore").strip().lower()

        return result if result in COMMIT_TYPES else "chore"
