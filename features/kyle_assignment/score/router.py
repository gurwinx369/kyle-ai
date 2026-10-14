from fastapi import APIRouter, Depends, HTTPException, status

from schemas.assignment import AssignmentScoreRequest, AssignmentScoreResponse
from utils.firebase.token_auth import verify_token
from core.trace import get_trace_id
from .service import score_assignment

router = APIRouter()


@router.post(
    "/assignment/score",
    response_model=AssignmentScoreResponse,
    status_code=status.HTTP_200_OK,
)
async def assignment_score(
    body: AssignmentScoreRequest,
    _token: dict = Depends(verify_token),
    trace_id: str = Depends(get_trace_id),
) -> AssignmentScoreResponse:
    try:
        user_id = _token.get("uid", "anonymous")
        return await score_assignment(body, user_id=user_id, trace_id=trace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

