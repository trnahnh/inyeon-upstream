from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from backend.core.dependencies import get_llm_from_request
from backend.models.schemas import AnalyzeRequest, AnalyzeResponse
from backend.prompts.analyze_prompt import build_analyze_prompt
from backend.services.llm import LLMProvider, LLMError


router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze git diff",
    description="Analyze a git diff and return structured insights about the changes.",
)
async def analyze_diff(
    request: AnalyzeRequest,
    llm: LLMProvider = Depends(get_llm_from_request),
) -> AnalyzeResponse:
    """
    Analyze a git diff and return:
    - Summary of changes
    - Impact assessment (low/medium/high)
    - Categories (feat, fix, refactor, etc.)
    - Breaking changes
    - Security concerns
    - Per-file change details
    """
    prompt = build_analyze_prompt(request.diff, request.context)

    try:
        result = await llm.generate(prompt, json_mode=True)
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM service error: {e}",
        )

    try:
        return AnalyzeResponse(**result)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM returned invalid response: {e.error_count()} validation errors",
        )
