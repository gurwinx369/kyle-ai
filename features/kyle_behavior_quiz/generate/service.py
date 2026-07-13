import uuid
from schemas.behavior_quiz import (
    CreateSessionRequest, CreateSessionResponse, QuizItemOut, EiStats
)
from core.behavior_engine import compute_e_i_incremental

def choose_difficulty_tier(prior_accuracy_rate):
    """
    PLACEHOLDER heuristic — replace with your real logic.
    No history -> start medium. High accuracy -> step up. Low -> step down.
    """
    if prior_accuracy_rate is None:
        return "medium"
    if prior_accuracy_rate >= 0.8:
        return "hard"
    if prior_accuracy_rate <= 0.4:
        return "easy"
    return "medium"

def generate_quiz_item(concept_ctx, difficulty_tier):
    """
    PLACEHOLDER — this is where the transcript+concept+level context gets
    sent to your LLM to generate the actual question/options/answer.
    Wire this to whatever Kyle already uses for single in-video quizzes.
    """
    return {
        "question": f"[generated question for '{concept_ctx.concept}' at {difficulty_tier}]",
        "options": ["Option A", "Option B", "Option C"],
        "correctOption": "Option A",
    }

def create_session_service(req: CreateSessionRequest) -> CreateSessionResponse:
    session_id = str(uuid.uuid4())
    quiz_items = []

    for ctx in req.targetConcepts:
        tier = choose_difficulty_tier(ctx.priorAccuracyRate)
        tier_stats = ctx.eiStats.get(tier, EiStats())
        e_i, _ = compute_e_i_incremental(tier_stats.eiCurrent, tier_stats.sampleCount, tier)

        generated = generate_quiz_item(ctx, tier)

        quiz_items.append(QuizItemOut(
            concept=ctx.concept,
            difficultyTier=tier,
            question=generated["question"],
            options=generated["options"],
            correctOption=generated["correctOption"],
            nOptions=len(generated["options"]),
            eiSnapshot=e_i,
            modelVersion=req.modelVersion,
        ))

    return CreateSessionResponse(sessionId=session_id, quizItems=quiz_items)
