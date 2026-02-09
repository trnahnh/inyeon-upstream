from unidiff import PatchSet

from .models import (
    ParsedDiff,
    ParsedFile,
    ParsedHunk,
    ParsedLine,
    LineType,
    FileChangeType,
)


class DiffParser:

    def parse(self, diff_text: str) -> ParsedDiff:
        if not diff_text.strip():
            return ParsedDiff()

        patch_set = PatchSet.from_string(diff_text)

        files = []
        for patched_file in patch_set:
            hunks = []
            for idx, hunk in enumerate(patched_file):
                parsed_hunk = ParsedHunk(
                    id=f"{patched_file.path}:{idx}",
                    source_start=hunk.source_start,
                    source_length=hunk.source_length,
                    target_start=hunk.target_start,
                    target_length=hunk.target_length,
                    section_header=hunk.section_header or "",
                    lines=[
                        ParsedLine(
                            content=line.value.rstrip("\n"),
                            line_type=self._map_line_type(line.line_type),
                            source_line_no=line.source_line_no,
                            target_line_no=line.target_line_no,
                        )
                        for line in hunk
                    ],
                    added_count=hunk.added,
                    removed_count=hunk.removed,
                )
                hunks.append(parsed_hunk)

            parsed_file = ParsedFile(
                path=patched_file.path,
                change_type=self._determine_change_type(patched_file),
                hunks=hunks,
                is_binary=patched_file.is_binary_file,
                old_path=patched_file.source_file if patched_file.is_rename else None,
            )
            files.append(parsed_file)

        return ParsedDiff(
            files=files,
            total_added=patch_set.added,
            total_removed=patch_set.removed,
        )

    def _determine_change_type(self, patched_file) -> FileChangeType:
        if patched_file.is_added_file:
            return FileChangeType.ADDED
        if patched_file.is_removed_file:
            return FileChangeType.DELETED
        if patched_file.is_rename:
            return FileChangeType.RENAMED
        return FileChangeType.MODIFIED

    def _map_line_type(self, unidiff_type: str) -> LineType:
        mapping = {
            "+": LineType.ADDED,
            "-": LineType.REMOVED,
            " ": LineType.CONTEXT,
        }
        return mapping.get(unidiff_type, LineType.CONTEXT)
