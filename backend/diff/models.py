"""
Data models for parsed git diffs.

These Pydantic models represent the structure of a git diff:
- ParsedDiff contains multiple ParsedFiles
- ParsedFile contains multiple ParsedHunks
- ParsedHunk contains multiple ParsedLines

"""

from enum import Enum
from pydantic import BaseModel, Field, computed_field


class LineType(str, Enum):
    """Type of change for a single line."""

    ADDED = "+"
    REMOVED = "-"
    CONTEXT = " "


class FileChangeType(str, Enum):
    """Type of change for a file."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class ParsedLine(BaseModel):
    """A single line in a diff hunk."""

    content: str
    line_type: LineType
    source_line_no: int | None = None  # Line number in old file
    target_line_no: int | None = None  # Line number in new file


class ParsedHunk(BaseModel):
    """
    A hunk (change block) within a file.
    """

    id: str = Field(description="Unique identifier: {file_path}:{hunk_index}")
    source_start: int = Field(description="Starting line in old file")
    source_length: int = Field(description="Number of lines in old file")
    target_start: int = Field(description="Starting line in new file")
    target_length: int = Field(description="Number of lines in new file")
    section_header: str = Field(
        default="", description="Function/class name from @@ line"
    )
    lines: list[ParsedLine] = Field(default_factory=list)
    added_count: int = 0
    removed_count: int = 0

    @computed_field
    @property
    def content(self) -> str:
        """Raw hunk content for embedding/display."""
        return "\n".join(line.content for line in self.lines)


class ParsedFile(BaseModel):
    """A file with its hunks."""

    path: str
    change_type: FileChangeType
    hunks: list[ParsedHunk] = Field(default_factory=list)
    is_binary: bool = False
    old_path: str | None = None  # For renames: the original path

    @computed_field
    @property
    def directory(self) -> str:
        """Extract parent directory."""
        import os

        return os.path.dirname(self.path) or "."

    @computed_field
    @property
    def extension(self) -> str:
        """Extract file extension."""
        import os

        return os.path.splitext(self.path)[1]


class ParsedDiff(BaseModel):
    """Complete parsed diff - the top-level container."""

    files: list[ParsedFile] = Field(default_factory=list)
    total_added: int = 0
    total_removed: int = 0

    def get_all_hunks(self) -> list[tuple[ParsedFile, ParsedHunk]]:
        """
        Flatten all hunks with their parent file for clustering.
        """
        return [(file, hunk) for file in self.files for hunk in file.hunks]
