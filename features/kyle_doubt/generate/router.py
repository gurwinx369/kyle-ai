from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from schemas.doubt import DoubtRequest, DoubtResponse
from utils.firebase.token_auth import verify_token
from .service import answer_doubt

router = APIRouter()


@router.post(
    "/doubt",
    response_model=DoubtResponse,
    status_code=status.HTTP_200_OK,
)
async def doubt_generate(
    body: DoubtRequest,
    _token: dict = Depends(verify_token),
) -> DoubtResponse | JSONResponse:
    try:
        answer = await answer_doubt(body)
        return DoubtResponse(answer=answer)
    except Exception as err:
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
                    "error": "Kyle is busy right now. Please try again in a few seconds.",
                    "retryable": True,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
