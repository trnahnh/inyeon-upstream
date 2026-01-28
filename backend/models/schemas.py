from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class ImpactLevel(str, Enum):
    """Severity of code changes."""

    LOW = "low"  # Typos, docs, formatting
    MEDIUM = "medium"  # Logic changes, new features
    HIGH = "high"  # Security, breaking changes, architecture


class ChangeType(str, Enum):
    """Type of file modification."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class CommitType(str, Enum):
    """Conventional commit types."""

    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"


# =============================================================================
# Shared Models
# =============================================================================


class FileChange(BaseModel):
    path: str = Field(..., description="File path relative to repo root")
    change_type: ChangeType = Field(..., description="Type of change")
    summary: str = Field(..., description="Brief description of changes")


# =============================================================================
# Analyze Endpoint
# =============================================================================


class AnalyzeRequest(BaseModel):
    diff: str = Field(..., min_length=1, description="Git diff content")
    context: Optional[str] = Field(
        None, description="Additional context about the changes"
    )


class AnalyzeResponse(BaseModel):
    summary: str = Field(..., description="Human-readable summary of changes")
    impact: ImpactLevel = Field(..., description="Overall impact assessment")
    categories: list[str] = Field(default_factory=list, description="Change categories")
    breaking_changes: list[str] = Field(
        default_factory=list, description="List of breaking changes"
    )
    security_concerns: list[str] = Field(
        default_factory=list, description="Security-related observations"
    )
    files_changed: list[FileChange] = Field(
        default_factory=list, description="Per-file change details"
    )


# =============================================================================
# Commit Endpoint
# =============================================================================


class CommitRequest(BaseModel):
    diff: str = Field(..., min_length=1, description="Git diff content")
    issue_ref: Optional[str] = Field(None, description="Issue reference (e.g., #234)")


class CommitResponse(BaseModel):
    message: str = Field(..., description="Full formatted commit message")
    type: CommitType = Field(..., description="Conventional commit type")
    scope: Optional[str] = Field(None, description="Commit scope (e.g., auth, api)")
    subject: str = Field(..., description="Commit subject line")
    body: Optional[str] = Field(None, description="Commit body with details")
    breaking_change: Optional[str] = Field(
        None, description="Breaking change description"
    )
    issue_refs: list[str] = Field(default_factory=list, description="Referenced issues")
