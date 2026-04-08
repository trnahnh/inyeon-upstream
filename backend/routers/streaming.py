from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.agents.changelog_agent import ChangelogAgent
from backend.agents.commit_agent import CommitAgent
from backend.agents.conflict_agent import ConflictAgent
from backend.agents.pr_agent import PRAgent
from backend.agents.review_agent import ReviewAgent
from backend.agents.split_agent import SplitAgent
from backend.core.dependencies import get_llm_from_request
from backend.models.events import EventType, StreamEvent
from backend.services.llm import LLMProvider


router = APIRouter(prefix="/agent/stream", tags=["streaming"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


async def sse_generator(events: AsyncIterator[StreamEvent]) -> AsyncIterator[str]:
    """Convert StreamEvent async iterator to SSE wire format."""
    try:
        async for event in events:
            yield f"event: {event.event.value}\ndata: {event.model_dump_json()}\n\n"
    except Exception as e:
        error = StreamEvent(
            event=EventType.ERROR, agent="", data={"error": str(e)}
        )
        yield f"event: error\ndata: {error.model_dump_json()}\n\n"


async def _error_stream(error: str) -> AsyncIterator[StreamEvent]:
    """Yield a single error event — used when agent creation fails."""
    yield StreamEvent(event=EventType.ERROR, data={"error": error})
    yield StreamEvent(event=EventType.DONE)


def _sse_response(events: AsyncIterator[StreamEvent]) -> StreamingResponse:
    return StreamingResponse(
        sse_generator(events),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


class StreamCommitRequest(BaseModel):
    diff: str = Field(..., min_length=1, max_length=50000)
    repo_path: str = Field(default=".")
    issue_ref: str | None = None


class StreamReviewRequest(BaseModel):
    diff: str = Field(..., min_length=1, max_length=50000)
    repo_path: str = Field(default=".")


class StreamPRRequest(BaseModel):
    diff: str = Field(..., min_length=1)
    commits: list[dict[str, str]] = Field(default_factory=list, max_length=500)
    branch_name: str = Field(default="")
    base_branch: str = Field(default="main")
    repo_path: str = Field(default=".")


class StreamSplitRequest(BaseModel):
    diff: str = Field(..., min_length=1, max_length=100000)
    repo_path: str = Field(default=".")
    strategy: Literal["directory", "semantic", "conventional", "hybrid"] = Field(
        default="hybrid"
    )


class StreamConflictFile(BaseModel):
    path: str
    content: str
    ours: str = ""
    theirs: str = ""


class StreamConflictRequest(BaseModel):
    conflicts: list[StreamConflictFile] = Field(..., min_length=1, max_length=50)
    repo_path: str = Field(default=".")


class StreamChangelogRequest(BaseModel):
    commits: list[dict[str, str]] = Field(..., min_length=1, max_length=500)
    from_ref: str = Field(default="")
    to_ref: str = Field(default="HEAD")
    repo_path: str = Field(default=".")


@router.post("/commit")
async def stream_commit(
    request: StreamCommitRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    diff = request.diff
    if request.issue_ref:
        diff = f"{diff}\n\nReference issue: {request.issue_ref}"
    try:
        agent = CommitAgent(llm=llm, retriever=None)
        return _sse_response(agent.run_stream(diff=diff, repo_path=request.repo_path))
    except Exception as e:
        return _sse_response(_error_stream(str(e)))


@router.post("/review")
async def stream_review(
    request: StreamReviewRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    try:
        agent = ReviewAgent(llm=llm, retriever=None)
        return _sse_response(agent.run_stream(diff=request.diff, repo_path=request.repo_path))
    except Exception as e:
        return _sse_response(_error_stream(str(e)))


@router.post("/pr")
async def stream_pr(
    request: StreamPRRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    try:
        agent = PRAgent(llm=llm, retriever=None)
        return _sse_response(
            agent.run_stream(
                diff=request.diff,
                commits=request.commits,
                branch_name=request.branch_name,
                base_branch=request.base_branch,
                repo_path=request.repo_path,
            )
        )
    except Exception as e:
        return _sse_response(_error_stream(str(e)))


@router.post("/split")
async def stream_split(
    request: StreamSplitRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    try:
        agent = SplitAgent(llm=llm, retriever=None)
        return _sse_response(
            agent.run_stream(
                diff=request.diff,
                repo_path=request.repo_path,
                strategy=request.strategy,
            )
        )
    except Exception as e:
        return _sse_response(_error_stream(str(e)))


@router.post("/resolve")
async def stream_resolve(
    request: StreamConflictRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    try:
        agent = ConflictAgent(llm=llm, retriever=None)
        conflicts = [c.model_dump() for c in request.conflicts]
        return _sse_response(
            agent.run_stream(conflicts=conflicts, repo_path=request.repo_path)
        )
    except Exception as e:
        return _sse_response(_error_stream(str(e)))


@router.post("/changelog")
async def stream_changelog(
    request: StreamChangelogRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    try:
        agent = ChangelogAgent(llm=llm, retriever=None)
        return _sse_response(
            agent.run_stream(
                commits=request.commits,
                from_ref=request.from_ref,
                to_ref=request.to_ref,
                repo_path=request.repo_path,
            )
        )
    except Exception as e:
        return _sse_response(_error_stream(str(e)))
