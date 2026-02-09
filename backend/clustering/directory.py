from backend.diff import ParsedDiff
from .base import ClusteringStrategy
from .models import CommitGroup, HunkReference


class DirectoryStrategy(ClusteringStrategy):

    name = "directory"
    description = "Group changes by parent directory"

    def __init__(self, max_depth: int = 2):
        self.max_depth = max_depth

    async def cluster(self, parsed_diff: ParsedDiff) -> list[CommitGroup]:
        groups: dict[str, CommitGroup] = {}

        for file in parsed_diff.files:
            dir_key = self._get_directory_key(file.path)

            if dir_key not in groups:
                groups[dir_key] = CommitGroup(
                    id=f"dir-{dir_key.replace('/', '-').replace('\\', '-')}",
                    hunks=[],
                    files=[],
                    suggested_scope=dir_key if dir_key != "root" else None,
                    reasoning=f"Files in {dir_key}/ directory",
                )

            groups[dir_key].files.append(file.path)
            for hunk in file.hunks:
                groups[dir_key].hunks.append(
                    HunkReference(file_path=file.path, hunk_id=hunk.id)
                )

        return list(groups.values())

    def _get_directory_key(self, path: str) -> str:
        import os

        parts = path.replace("\\", "/").split("/")[:-1]
        if not parts:
            return "root"
        return "/".join(parts[: self.max_depth])
