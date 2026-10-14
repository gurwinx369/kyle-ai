from fastapi import APIRouter, Depends, HTTPException, status

from schemas.assignment import AssignmentGenerateRequest, AssignmentGenerateResponse
from utils.firebase.token_auth import verify_token
from core.trace import get_trace_id
from .service import generate_assignment

router = APIRouter()


@router.post(
    "/assignment/generate",
    response_model=AssignmentGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def assignment_generate(
    body: AssignmentGenerateRequest,
    _token: dict = Depends(verify_token),
    trace_id: str = Depends(get_trace_id),
) -> AssignmentGenerateResponse:
    try:
        user_id = _token.get("uid", "anonymous")
        assignment_prompt = await generate_assignment(body, user_id=user_id, trace_id=trace_id)
        return AssignmentGenerateResponse(
            assignment_prompt=assignment_prompt,
            conversation_id=trace_id,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

