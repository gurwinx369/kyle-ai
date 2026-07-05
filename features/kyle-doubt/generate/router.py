import importlib.util
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from schemas.doubt import DoubtRequest, DoubtResponse
from utils.firebase.token_auth import verify_token

# Load service from same directory — parent dir uses hyphens, not importable as a package.
_spec = importlib.util.spec_from_file_location(
    "_kyle_doubt_gen_svc", Path(__file__).parent / "service.py"
)
_svc = importlib.util.module_from_spec(_spec)
sys.modules["_kyle_doubt_gen_svc"] = _svc
_spec.loader.exec_module(_svc)

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
        answer = await _svc.answer_doubt(body)
        return DoubtResponse(answer=answer)
    except Exception as err:
        msg = str(err).lower()
        if (
            "503" in msg
            or "service unavailable" in msg
            or "high demand" in msg
            or "try again" in msg
        ):
            # This handles the case where the retry ALSO failed.
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
