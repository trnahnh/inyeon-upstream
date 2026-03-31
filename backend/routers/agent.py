from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.agents import CommitAgent, ReviewAgent, AgentOrchestrator
from backend.core.logging import logger
from backend.services.llm import LLMProvider, LLMError
from backend.core.dependencies import get_llm_from_request


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRequest(BaseModel):
    diff: str = Field(..., min_length=1, max_length=50000)
    repo_path: str = Field(default=".")
    verbose: bool = Field(default=False)


class AgentCommitResponse(BaseModel):
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


@router.post("/run", response_model=AgentCommitResponse)
async def run_commit_agent(
    request: AgentRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    try:
        agent = CommitAgent(llm)
        result = await agent.run(diff=request.diff, repo_path=request.repo_path)

        return AgentCommitResponse(
            commit_message=result["commit_message"] or "",
            reasoning=result["reasoning"] if request.verbose else [],
            analysis=result.get("analysis", {}) if request.verbose else {},
        )
    except LLMError as e:
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    except Exception as e:
        logger.error("commit agent failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/review", response_model=ReviewResponse)
async def run_review_agent(
    request: AgentRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    try:
        agent = ReviewAgent(llm)
        result = await agent.run(diff=request.diff, repo_path=request.repo_path)

        return ReviewResponse(
            review=result.get("review", {}),
            reasoning=result["reasoning"] if request.verbose else [],
        )
    except LLMError as e:
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    except Exception as e:
        logger.error("review agent failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/orchestrate")
async def orchestrate(
    request: OrchestrationRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
):
    try:
        orchestrator = AgentOrchestrator(llm)
        result = await orchestrator.route(
            task=request.task,
            diff=request.diff,
            repo_path=request.repo_path,
        )
        return result
    except LLMError as e:
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    except Exception as e:
        logger.error("orchestrator failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/list")
async def list_agents(llm: LLMProvider = Depends(get_llm_from_request)):
    orchestrator = AgentOrchestrator(llm)
    return {"agents": orchestrator.list_agents()}
