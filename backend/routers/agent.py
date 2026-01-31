from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.agents import CommitAgent, ReviewAgent, AgentOrchestrator
from backend.services.llm import create_llm_provider, LLMProvider
from backend.core.config import settings


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRequest(BaseModel):
    diff: str = Field(..., min_length=1, max_length=50000)
    repo_path: str = Field(default=".")
    verbose: bool = Field(default=False)


class CommitResponse(BaseModel):
    commit_message: str
    reasoning: list[str] = []
    analysis: dict[str, Any] = {}


class ReviewResponse(BaseModel):
    review: dict[str, Any]
    reasoning: list[str] = []


class OrchestrationRequest(BaseModel):
    task: str = Field(..., description="Task description or agent name")
    diff: str = Field(..., min_length=1, max_length=50000)
    repo_path: str = Field(default=".")


def get_llm() -> LLMProvider:
    """Dependency that provides the configured LLM provider."""
    return create_llm_provider(
        provider=settings.llm_provider,
        ollama_url=settings.ollama_url,
        ollama_model=settings.ollama_model,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        timeout=settings.ollama_timeout,
    )


@router.post("/run", response_model=CommitResponse)
async def run_commit_agent(
    request: AgentRequest,
    llm: LLMProvider = Depends(get_llm),
):
    """Run the commit agent to generate commit messages."""
    try:
        agent = CommitAgent(llm)
        result = await agent.run(diff=request.diff, repo_path=request.repo_path)

        return CommitResponse(
            commit_message=result["commit_message"] or "",
            reasoning=result["reasoning"] if request.verbose else [],
            analysis=result.get("analysis", {}) if request.verbose else {},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review", response_model=ReviewResponse)
async def run_review_agent(
    request: AgentRequest,
    llm: LLMProvider = Depends(get_llm),
):
    """Run the review agent to get code feedback."""
    try:
        agent = ReviewAgent(llm)
        result = await agent.run(diff=request.diff, repo_path=request.repo_path)

        return ReviewResponse(
            review=result.get("review", {}),
            reasoning=result["reasoning"] if request.verbose else [],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orchestrate")
async def orchestrate(
    request: OrchestrationRequest,
    llm: LLMProvider = Depends(get_llm),
):
    """Route to appropriate agent based on task."""
    try:
        orchestrator = AgentOrchestrator(llm)
        result = await orchestrator.route(
            task=request.task,
            diff=request.diff,
            repo_path=request.repo_path,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_agents(llm: LLMProvider = Depends(get_llm)):
    """List available agents."""
    orchestrator = AgentOrchestrator(llm)
    return {"agents": orchestrator.list_agents()}
