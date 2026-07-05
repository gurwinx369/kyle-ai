from pydantic import BaseModel

from schemas.common import RoleEnum


class QuizOptions(BaseModel):
    A: str
    B: str
    C: str


class QuizGenerateRequest(BaseModel):
    concept: str
    transcript: str
    role: RoleEnum


class QuizGenerateResponse(BaseModel):
    question: str
    options: QuizOptions
    correct_answer: str
    explanation: str
