from fastapi import APIRouter, Depends

from schemas.behavior_quiz import CreateSessionRequest, CreateSessionResponse
from core.trace import get_trace_id
from .service import create_session_service

router = APIRouter(prefix="/behavior")


@router.post("/session/create", response_model=CreateSessionResponse)
async def create_session(
    req: CreateSessionRequest,
    trace_id: str = Depends(get_trace_id),
):
    return await create_session_service(req, user_id=req.userId, trace_id=trace_id)