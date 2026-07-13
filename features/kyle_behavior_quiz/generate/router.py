from fastapi import APIRouter

from schemas.behavior_quiz import CreateSessionRequest, CreateSessionResponse
from .service import create_session_service

router = APIRouter(prefix="/behavior")


@router.post("/session/create", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest):
    return create_session_service(req)