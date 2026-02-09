from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from backend.agents.split_agent import SplitAgent
from backend.services.llm import create_llm_provider, LLMProvider
from backend.core.config import settings


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


def get_llm() -> LLMProvider:
    return create_llm_provider(
        provider=settings.llm_provider,
        ollama_url=settings.ollama_url,
        ollama_model=settings.ollama_model,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        timeout=settings.ollama_timeout,
    )


@router.post("/agent/split", response_model=SplitResponse)
async def split_diff(
    request: SplitRequest,
    llm: LLMProvider = Depends(get_llm),
):
    try:
        agent = SplitAgent(llm=llm, retriever=None)
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
