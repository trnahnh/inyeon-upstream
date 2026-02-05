from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Literal

from backend.agents.split_agent import SplitAgent
from backend.core.dependencies import get_llm_provider, get_retriever
from backend.services.llm.base import LLMProvider
from backend.rag.retriever import CodeRetriever


router = APIRouter(tags=["agent"])


class SplitRequest(BaseModel):
    diff: str = Field(..., min_length=1, max_length=100000)
    repo_path: str = Field(default=".")
    strategy: Literal["directory", "semantic", "conventional", "hybrid"] = Field(
        default="hybrid"
    )


class CommitGroupResponse(BaseModel):
    group_id: str
    files: list[str]
    hunk_count: int
    commit_message: str
    commit_type: str | None = None
    scope: str | None = None


class SplitResponse(BaseModel):
    splits: list[CommitGroupResponse] = Field(default_factory=list)
    total_groups: int
    reasoning: list[str] = Field(default_factory=list)
    error: str | None = None


@router.post("/agent/split", response_model=SplitResponse)
async def split_diff(
    request: SplitRequest,
    llm: LLMProvider = Depends(get_llm_provider),
    retriever: CodeRetriever | None = Depends(get_retriever),
):
    agent = SplitAgent(llm=llm, retriever=retriever)
    result = await agent.run(
        diff=request.diff,
        repo_path=request.repo_path,
        strategy=request.strategy,
    )

    return SplitResponse(
        splits=[CommitGroupResponse(**s) for s in result["splits"]],
        total_groups=result["total_groups"],
        reasoning=result["reasoning"],
        error=result.get("error"),
    )
