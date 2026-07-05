import importlib.util
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from schemas.quiz import QuizGenerateRequest, QuizGenerateResponse
from utils.firebase.token_auth import verify_token

# Load service from same directory — parent dir uses hyphens, not importable as a package.
_spec = importlib.util.spec_from_file_location(
    "_kyle_quiz_gen_svc", Path(__file__).parent / "service.py"
)
_svc = importlib.util.module_from_spec(_spec)
sys.modules["_kyle_quiz_gen_svc"] = _svc
_spec.loader.exec_module(_svc)

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
        return await _svc.generate_quiz(body)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
