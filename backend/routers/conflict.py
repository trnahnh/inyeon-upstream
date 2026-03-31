from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.agents.conflict_agent import ConflictAgent
from backend.services.llm import LLMProvider
from backend.core.dependencies import get_llm_from_request


router = APIRouter(tags=["agent"])


class ConflictFile(BaseModel):
    path: str
    content: str
    ours: str = ""
    theirs: str = ""


class ConflictRequest(BaseModel):
    conflicts: list[ConflictFile] = Field(..., min_length=1)
    repo_path: str = Field(default=".")


class ConflictResponse(BaseModel):
    resolutions: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    error: str | None = None


@router.post("/agent/resolve", response_model=ConflictResponse)
async def resolve_conflicts(
    request: ConflictRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    try:
        agent = ConflictAgent(llm=llm, retriever=None)
        conflicts = [c.model_dump() for c in request.conflicts]
        result = await agent.run(conflicts=conflicts, repo_path=request.repo_path)
        return ConflictResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
