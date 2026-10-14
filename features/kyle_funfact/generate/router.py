from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from schemas.funfact import FunFactRequest, FunFactResponse
from utils.firebase.token_auth import verify_token
from core.trace import get_trace_id
from .service import generate_fun_fact

router = APIRouter()

@router.post(
    "/funfact",
    response_model=FunFactResponse,
    status_code=status.HTTP_200_OK,
)
async def funfact_generate(
    body: FunFactRequest,
    _token: dict = Depends(verify_token),
    trace_id: str = Depends(get_trace_id),
) -> FunFactResponse | JSONResponse:
    try:
        user_id = _token.get("uid", "anonymous")
        fun_fact = await generate_fun_fact(body, user_id=user_id, trace_id=trace_id)
        return FunFactResponse(fun_fact=fun_fact, conversation_id=trace_id)

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
                    "error": "Kibo is busy right now. Please try again in a few seconds.",
                    "retryable": True,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
