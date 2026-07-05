import importlib.util
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from schemas.assignment import AssignmentGenerateRequest, AssignmentGenerateResponse
from utils.firebase.token_auth import verify_token

# Load service from same directory — parent dir uses hyphens, not importable as a package.
_spec = importlib.util.spec_from_file_location(
    "_kyle_asgn_gen_svc", Path(__file__).parent / "service.py"
)
_svc = importlib.util.module_from_spec(_spec)
sys.modules["_kyle_asgn_gen_svc"] = _svc
_spec.loader.exec_module(_svc)

router = APIRouter()


@router.post(
    "/assignment/generate",
    response_model=AssignmentGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def assignment_generate(
    body: AssignmentGenerateRequest,
    _token: dict = Depends(verify_token),
) -> AssignmentGenerateResponse:
    try:
        assignment_prompt = await _svc.generate_assignment(body)
        return AssignmentGenerateResponse(assignment_prompt=assignment_prompt)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
