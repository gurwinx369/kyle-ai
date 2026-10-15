import logging

from fastapi import APIRouter, Depends, HTTPException, status

from schemas.quiz import QuizGenerateRequest, QuizGenerateResponse
from utils.firebase.token_auth import verify_token
from core.trace import get_trace_id
from .service import generate_quiz

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/quiz/generate",
    response_model=QuizGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def quiz_generate(
    body: QuizGenerateRequest,
    _token: dict = Depends(verify_token),
    trace_id: str = Depends(get_trace_id),
) -> QuizGenerateResponse:
    try:
        user_id = _token.get("uid", "anonymous")
        return await generate_quiz(body, user_id=user_id, trace_id=trace_id)
    except Exception as exc:
        logger.exception("[quiz_generate] Error generating quiz: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

