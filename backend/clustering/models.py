from pydantic import BaseModel, Field, computed_field


class HunkReference(BaseModel):
    file_path: str
    hunk_id: str


class CommitGroup(BaseModel):
    id: str
    hunks: list[HunkReference] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    suggested_type: str | None = None
    suggested_scope: str | None = None
    reasoning: str = ""
    commit_message: str | None = None

    @computed_field
    @property
    def file_count(self) -> int:
        return len(set(self.files))

    @computed_field
    @property
    def hunk_count(self) -> int:
        return len(self.hunks)
