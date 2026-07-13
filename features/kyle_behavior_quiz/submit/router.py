from fastapi import APIRouter

from schemas.behavior_quiz import GradeSessionRequest, GradeSessionResponse
from .service import grade_session_service

router = APIRouter(prefix="/behavior")


@router.post("/session/grade", response_model=GradeSessionResponse)
def grade_session(req: GradeSessionRequest):
    return grade_session_service(req)
