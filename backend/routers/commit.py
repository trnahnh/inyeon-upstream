from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from backend.core.dependencies import get_llm_from_request
from backend.models.schemas import CommitRequest, CommitResponse
from backend.prompts.commit_prompt import build_commit_prompt
from backend.services.llm import LLMProvider, LLMError


router = APIRouter()


@router.post(
    "/generate-commit",
    response_model=CommitResponse,
    summary="Generate commit message",
    description="Generate a conventional commit message from a git diff.",
)
async def generate_commit(
    request: CommitRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
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
        result = await llm.generate(prompt, json_mode=True)
    except LLMError as e:
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
