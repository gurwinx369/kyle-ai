import asyncio
import json
import random
import re
import uuid

from schemas.behavior_quiz import (
    CreateSessionRequest, CreateSessionResponse, QuizItemOut, EiStats,
)
from core.behavior_engine import compute_e_i_incremental
from core.gemini_client import generate
from utils.prompts.system_prompts import build_behavior_quiz_prompt

_OPTION_KEYS = ["A", "B", "C"]


def _parse_json(raw: str) -> dict:
    """Strip markdown fences Gemini sometimes wraps around JSON responses."""
    cleaned = re.sub(r"^```json\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    if not cleaned:
        raise ValueError("Gemini response was empty after stripping markdown fences.")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        snippet = cleaned[:200]
        raise ValueError(
            f"Gemini response is not valid JSON: {exc}. Content snippet: {snippet!r}"
        ) from exc


def _shuffle_options(quiz: dict) -> dict:
    """Randomise A/B/C order while keeping correctAnswer in sync."""
    correct_key = str(quiz.get("correctAnswer", "")).strip().upper()[:1]
    if correct_key not in _OPTION_KEYS:
        raise ValueError(f"Invalid correctAnswer from Gemini: {correct_key!r}")

    items = []
    for key in _OPTION_KEYS:
        text = str(quiz["options"].get(key, "")).strip()
        if not text:
            raise ValueError(f"Option {key!r} is empty in Gemini response")
        items.append({"text": text, "is_correct": key == correct_key})

    random.shuffle(items)

    options: dict[str, str] = {}
    new_correct: str | None = None
    for i, item in enumerate(items):
        new_key = _OPTION_KEYS[i]
        options[new_key] = item["text"]
        if item["is_correct"]:
            new_correct = new_key

    if new_correct is None:
        raise ValueError("Failed to locate correct answer after shuffle")

    return {**quiz, "options": options, "correctAnswer": new_correct}


def _choose_difficulty_tier(prior_accuracy_rate: float | None) -> str:
    if prior_accuracy_rate is None:
        return "medium"
    if prior_accuracy_rate >= 0.8:
        return "hard"
    if prior_accuracy_rate <= 0.4:
        return "easy"
    return "medium"


async def _generate_one_item(concept_ctx, difficulty_tier: str) -> dict:
    system_instruction = build_behavior_quiz_prompt(
        concept=concept_ctx.concept,
        transcript=concept_ctx.transcriptContext,
        level_context=concept_ctx.levelContext,
        difficulty_tier=difficulty_tier,
    )
    last_err: Exception | None = None
    for attempt in range(3):
        raw = await generate(
            system_instruction=system_instruction,
            user_text="Generate the quiz question.",
            temperature=0,
        )
        try:
            quiz = _parse_json(raw)
            return _shuffle_options(quiz)
        except ValueError as exc:
            last_err = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))
    raise RuntimeError(
        f"Failed to generate a valid quiz item for concept {concept_ctx.concept!r} "
        f"after 3 attempts. Last error: {last_err}"
    )


async def create_session_service(req: CreateSessionRequest) -> CreateSessionResponse:
    session_id = str(uuid.uuid4())

    # Resolve tier and E_i per concept up front (synchronous, no I/O)
    tiers: list[str] = []
    ei_snapshots: list[float] = []
    for ctx in req.targetConcepts:
        tier = _choose_difficulty_tier(ctx.priorAccuracyRate)
        tier_stats = ctx.eiStats.get(tier, EiStats())
        e_i, _ = compute_e_i_incremental(tier_stats.eiCurrent, tier_stats.sampleCount, tier)
        tiers.append(tier)
        ei_snapshots.append(e_i)

    # Generate all questions concurrently — one Gemini call per concept
    generated_items = await asyncio.gather(
        *[_generate_one_item(ctx, tiers[i]) for i, ctx in enumerate(req.targetConcepts)]
    )

    quiz_items = [
        QuizItemOut(
            concept=ctx.concept,
            difficultyTier=tiers[i],
            question=generated_items[i]["question"],
            options=list(generated_items[i]["options"].values()),
            correctOption=generated_items[i]["options"][generated_items[i]["correctAnswer"]],
            nOptions=len(generated_items[i]["options"]),
            eiSnapshot=ei_snapshots[i],
            modelVersion=req.modelVersion,
        )
        for i, ctx in enumerate(req.targetConcepts)
    ]
    return CreateSessionResponse(sessionId=session_id, quizItems=quiz_items)
