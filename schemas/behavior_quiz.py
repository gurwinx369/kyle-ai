"""
schemas.py — Pydantic contracts for the two endpoints Next.js calls.
FastAPI never touches Mongo. Every field it needs to grade or classify
must arrive in the request; every derived value it produces must be
returned for Next.js to persist.
"""

from pydantic import BaseModel
from typing import Optional, Literal

SpeedBucket = Literal["FAST", "MEDIUM", "SLOW", "GRACE", "UNATTEMPTED"]
Verdict = Literal["INSUFFICIENT_DATA", "MASTERY", "KNOWLEDGE_GAP", "DISENGAGED_GUESSING", "DEVELOPING"]
DifficultyTier = Literal["easy", "medium", "hard"]


# ============================================================
# Step 2: Next.js -> FastAPI, "create session" (fires after every 3rd
# concept completion, once BehaviorQuizHistory.recordConceptCompletion
# returns fired=true)
# ============================================================
class EiStats(BaseModel):
    eiCurrent: Optional[float] = None   # None = true cold start for this (concept, tier)
    sampleCount: int = 0

class TargetConceptContext(BaseModel):
    concept: str
    transcriptContext: str
    levelContext: str
    priorAccuracyRate: Optional[float] = None  # used for difficulty selection; None if no history
    eiStats: dict[DifficultyTier, EiStats] = {}  # keyed by tier, since concept may span tiers over time

class CreateSessionRequest(BaseModel):
    userId: str
    targetConcepts: list[TargetConceptContext]  # length 3, per the trigger design
    modelVersion: str = "v1"

class QuizItemOut(BaseModel):
    concept: str
    difficultyTier: DifficultyTier
    question: str
    options: list[str]
    correctOption: str          # answer key — sent to frontend deliberately, for instant client-side feedback
    nOptions: int
    eiSnapshot: float           # E_i used for this item, needed again at grading time
    modelVersion: str

class CreateSessionResponse(BaseModel):
    sessionId: str
    quizItems: list[QuizItemOut]


# ============================================================
# Step 4: Next.js -> FastAPI, "grade session" (after the lazy/silent
# background submit from the client)
# ============================================================
class PriorAttempt(BaseModel):
    """A previously graded attempt for this concept, pulled by Next.js from
    BehaviorQuizHistory before calling FastAPI — needed to pool evidence
    across sessions for classify_concept, since FastAPI holds no history."""
    wasCorrect: bool
    speedBucket: SpeedBucket
    rgbFlag: bool
    llrContribution: Optional[float]
    nOptions: int

class SubmittedAttempt(BaseModel):
    concept: str
    difficultyTier: DifficultyTier
    question: str                # read from stored session shell by Next.js, echoed back in GradedAttemptOut
    selectedOption: str
    correctOption: str
    responseTimeMs: int
    nOptions: int
    eiSnapshot: float            # the E_i stored in the session shell at trigger time
    modelVersion: str

class GradeSessionRequest(BaseModel):
    userId: str
    sessionId: str
    submittedAttempts: list[SubmittedAttempt]                  # the 3 just-answered items
    priorAttemptsByConcept: dict[str, list[PriorAttempt]] = {} # history for pooling, keyed by concept
    eiStatsByConceptTier: dict[str, EiStats] = {}               # keyed "concept::tier", current stats to update

class GradedAttemptOut(BaseModel):
    concept: str
    difficultyTier: DifficultyTier
    question: str                # passed through from SubmittedAttempt — Next.js persists this to MongoDB
    wasCorrect: bool
    responseTimeMs: int
    speedBucket: SpeedBucket
    rgbFlag: bool
    llrContribution: Optional[float]
    nOptions: int
    modelVersion: str

class ConceptVerdictOut(BaseModel):
    verdict: Verdict
    nAttempts: int
    posterior: Optional[float] = None
    llr_total: Optional[float] = None
    pChance: Optional[float] = None
    rgbCount: Optional[int] = None

class GradeSessionResponse(BaseModel):
    gradedAttempts: list[GradedAttemptOut]
    updatedEiStats: dict[str, EiStats]          # keyed "concept::tier" — Next.js overwrites its stored values with these
    conceptVerdicts: dict[str, ConceptVerdictOut]  # keyed by concept