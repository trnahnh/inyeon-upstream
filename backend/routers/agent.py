from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.agents import GitAgent
from backend.core.dependencies import get_ollama_client
from backend.services.llm import OllamaProvider
from backend.core.config import settings


router = APIRouter(prefix="/agent", tags=["Agent"])


class AgentRequest(BaseModel):
    diff: str = Field(..., min_length=1, max_length=50000)
    repo_path: str = Field(default=".")
    verbose: bool = Field(default=False)


class AgentResponse(BaseModel):
    commit_message: str
    reasoning: list[str] = []
    analysis: dict[str, Any] = {}


def get_llm_provider() -> OllamaProvider:
    """Dependency that provides the LLM provider."""
    return OllamaProvider(
        base_url=settings.ollama_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout,
    )


@router.post("/run", response_model=AgentResponse)
async def run_agent(
    request: AgentRequest,
    llm: OllamaProvider = Depends(get_llm_provider),
):
    """Run the git workflow agent."""
    try:
        agent = GitAgent(llm)
        result = await agent.run(
            diff=request.diff,
            repo_path=request.repo_path,
        )

        return AgentResponse(
            commit_message=result["commit_message"] or "",
            reasoning=result["reasoning"] if request.verbose else [],
            analysis=result.get("analysis", {}) if request.verbose else {},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
