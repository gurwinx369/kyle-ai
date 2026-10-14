from typing import Optional
from pydantic import BaseModel, model_validator

from schemas.common import ModeEnum, RoleEnum


class Message(BaseModel):
    role: str  # "user" or "model"
    text: str


class DoubtRequest(BaseModel):
    mode: Optional[ModeEnum] = None
    concept: Optional[str] = None
    transcript: Optional[str] = None
    role: RoleEnum
    question: str
    pageContext: Optional[str] = None
    history: Optional[list[Message]] = []

    @model_validator(mode="after")
    def require_context_for_contextual_mode(self) -> "DoubtRequest":
        if self.mode == ModeEnum.general:
            return self
        has_context = bool(self.concept and self.concept.strip()) and bool(
            self.transcript and self.transcript.strip()
        )
        if not has_context:
            raise ValueError(
                "concept and transcript are required for contextual requests"
            )
        return self

    @model_validator(mode="after")
    def validate_question_length(self) -> "DoubtRequest":
        if not self.question or not self.question.strip():
            raise ValueError("question must not be empty")
        if len(self.question) > 500:
            raise ValueError("question must be 500 characters or fewer")
        return self


class DoubtResponse(BaseModel):
    answer: str
    conversation_id: Optional[str] = None
