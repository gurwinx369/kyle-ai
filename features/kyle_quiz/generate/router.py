from fastapi import APIRouter, Depends, HTTPException, status

from schemas.quiz import QuizGenerateRequest, QuizGenerateResponse
from utils.firebase.token_auth import verify_token
from .service import generate_quiz

router = APIRouter()


@router.post(
    "/quiz/generate",
    response_model=QuizGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def quiz_generate(
    body: QuizGenerateRequest,
    _token: dict = Depends(verify_token),
) -> QuizGenerateResponse:
    try:
        return await generate_quiz(body)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
