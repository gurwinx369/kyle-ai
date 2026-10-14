from typing import List, Optional

from pydantic import BaseModel, field_validator

from schemas.common import RoleEnum


class Level(BaseModel):
    concept: str
    transcript: str

    @field_validator("concept", "transcript")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v


class AssignmentGenerateRequest(BaseModel):
    role: RoleEnum
    day_number: int
    levels: List[Level]

    @field_validator("day_number")
    @classmethod
    def day_number_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("day_number must be a positive integer")
        return v

    @field_validator("levels")
    @classmethod
    def levels_must_not_be_empty(cls, v: List[Level]) -> List[Level]:
        if not v:
            raise ValueError("levels must contain at least one item")
        return v


class AssignmentGenerateResponse(BaseModel):
    assignment_prompt: str
    conversation_id: Optional[str] = None


class AssignmentScoreRequest(BaseModel):
    role: RoleEnum
    day_number: int
    levels: List[Level]
    assignment_prompt: str
    user_response: str

    @field_validator("day_number")
    @classmethod
    def day_number_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("day_number must be a positive integer")
        return v

    @field_validator("levels")
    @classmethod
    def levels_must_not_be_empty(cls, v: List[Level]) -> List[Level]:
        if not v:
            raise ValueError("levels must contain at least one item")
        return v

    @field_validator("assignment_prompt", "user_response")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v


class ScoreBreakdown(BaseModel):
    topic_relevance: int
    concept_application: int
    prompt_quality: int
    role_aptitude: int


class AssignmentScoreResponse(BaseModel):
    score: int
    feedback: str
    passed: bool
    breakdown: ScoreBreakdown
    weaknesses: List[str]
    conversation_id: Optional[str] = None
