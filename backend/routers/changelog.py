from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.agents.changelog_agent import ChangelogAgent
from backend.services.llm import create_llm_provider, LLMProvider
from backend.core.config import settings


router = APIRouter(tags=["agent"])


class ChangelogRequest(BaseModel):
    commits: list[dict[str, str]] = Field(..., min_length=1)
    from_ref: str = Field(default="")
    to_ref: str = Field(default="HEAD")
    repo_path: str = Field(default=".")


class ChangelogResponse(BaseModel):
    changelog: dict[str, Any] | None = None
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


@router.post("/agent/changelog", response_model=ChangelogResponse)
async def generate_changelog(
    request: ChangelogRequest,
    llm: LLMProvider = Depends(get_llm),
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
