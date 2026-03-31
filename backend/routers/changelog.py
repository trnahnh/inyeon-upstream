from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.agents.changelog_agent import ChangelogAgent
from backend.core.logging import logger
from backend.services.llm import LLMProvider, LLMError
from backend.core.dependencies import get_llm_from_request


router = APIRouter(tags=["agent"])


class ChangelogRequest(BaseModel):
    commits: list[dict[str, str]] = Field(..., min_length=1, max_length=500)
    from_ref: str = Field(default="")
    to_ref: str = Field(default="HEAD")
    repo_path: str = Field(default=".")


class ChangelogResponse(BaseModel):
    changelog: dict[str, Any] | None = None
    reasoning: list[str] = Field(default_factory=list)
    error: str | None = None


@router.post("/agent/changelog", response_model=ChangelogResponse)
async def generate_changelog(
    request: ChangelogRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    try:
        agent = ChangelogAgent(llm=llm, retriever=None)
        result = await agent.run(
            commits=request.commits,
            from_ref=request.from_ref,
            to_ref=request.to_ref,
            repo_path=request.repo_path,
        )
        return ChangelogResponse(**result)
    except LLMError:
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    except Exception as e:
        logger.error("changelog agent failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
