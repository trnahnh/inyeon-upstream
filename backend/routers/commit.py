from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from backend.core.dependencies import get_ollama_client
from backend.models.schemas import CommitRequest, CommitResponse
from backend.prompts.commit_prompt import build_commit_prompt
from backend.services.ollama_client import OllamaClient, OllamaError


router = APIRouter()


@router.post(
    "/generate-commit",
    response_model=CommitResponse,
    summary="Generate commit message",
    description="Generate a conventional commit message from a git diff.",
)
async def generate_commit(
    request: CommitRequest,
    ollama: OllamaClient = Depends(get_ollama_client),
) -> CommitResponse:
    """
    Generate a conventional commit message including:
    - Type (feat, fix, refactor, etc.)
    - Scope (optional)
    - Subject line
    - Body (optional)
    - Breaking change notice (if applicable)
    - Issue references
    """
    prompt = build_commit_prompt(request.diff, request.issue_ref)

    try:
        result = await ollama.generate(prompt, json_mode=True)
    except OllamaError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM service error: {e}",
        )

    try:
        return CommitResponse(**result)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM returned invalid response: {e.error_count()} validation errors",
        )
