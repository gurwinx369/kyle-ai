import importlib.util
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from schemas.assignment import AssignmentScoreRequest, AssignmentScoreResponse
from utils.firebase.token_auth import verify_token

# Load service from same directory — parent dir uses hyphens, not importable as a package.
_spec = importlib.util.spec_from_file_location(
    "_kyle_asgn_score_svc", Path(__file__).parent / "service.py"
)
_svc = importlib.util.module_from_spec(_spec)
sys.modules["_kyle_asgn_score_svc"] = _svc
_spec.loader.exec_module(_svc)

router = APIRouter()


@router.post(
    "/assignment/score",
    response_model=AssignmentScoreResponse,
    status_code=status.HTTP_200_OK,
)
async def assignment_score(
    body: AssignmentScoreRequest,
    _token: dict = Depends(verify_token),
) -> AssignmentScoreResponse:
    try:
        return await _svc.score_assignment(body)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
