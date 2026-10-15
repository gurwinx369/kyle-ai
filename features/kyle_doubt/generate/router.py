import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from schemas.doubt import DoubtRequest, DoubtResponse
from utils.firebase.token_auth import verify_token
from core.trace import get_trace_id
from .service import answer_doubt

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/doubt",
    response_model=DoubtResponse,
    status_code=status.HTTP_200_OK,
)
async def doubt_generate(
    body: DoubtRequest,
    _token: dict = Depends(verify_token),
    trace_id: str = Depends(get_trace_id),
) -> DoubtResponse | JSONResponse:
    try:
        user_id = _token.get("uid", "anonymous")
        answer = await answer_doubt(body, user_id=user_id, trace_id=trace_id)
        return DoubtResponse(answer=answer, conversation_id=trace_id)

    except Exception as err:
        logger.exception("[doubt_generate] Error: %s", err)
        msg = str(err).lower()
        if (
            "503" in msg
            or "service unavailable" in msg
            or "high demand" in msg
            or "try again" in msg
        ):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Kibo is busy right now. Please try again in a few seconds.",
                    "retryable": True,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
