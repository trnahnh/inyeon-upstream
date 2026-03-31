from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from backend.agents.split_agent import SplitAgent
from backend.core.logging import logger
from backend.services.llm import LLMProvider, LLMError
from backend.core.dependencies import get_llm_from_request


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
    llm: LLMProvider = Depends(get_llm_from_request),
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
    except LLMError:
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    except Exception as e:
        logger.error("split agent failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
