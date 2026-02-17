from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.agents.pr_agent import PRAgent
from backend.services.llm import create_llm_provider, LLMProvider
from backend.core.config import settings


router = APIRouter(tags=["agent"])


class PRRequest(BaseModel):
    diff: str = Field(..., min_length=1, max_length=100000)
    commits: list[dict[str, str]] = Field(default_factory=list)
    branch_name: str = Field(default="")
    base_branch: str = Field(default="main")
    repo_path: str = Field(default=".")


class PRResponse(BaseModel):
    pr_description: dict[str, Any] | None = None
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


@router.post("/agent/pr", response_model=PRResponse)
async def generate_pr(
    request: PRRequest,
    llm: LLMProvider = Depends(get_llm),
):
    try:
        agent = PRAgent(llm=llm, retriever=None)
        result = await agent.run(
            diff=request.diff,
            commits=request.commits,
            branch_name=request.branch_name,
            base_branch=request.base_branch,
            repo_path=request.repo_path,
        )
        return PRResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
