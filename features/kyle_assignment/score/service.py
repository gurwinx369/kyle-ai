import json
import re

from core.gemini_client import generate
from schemas.assignment import (
    AssignmentScoreRequest,
    AssignmentScoreResponse,
    ScoreBreakdown,
)
from utils.prompts.role_context import get_role_context
from utils.prompts.system_prompts import build_scoring_prompt


def _build_day_context(levels: list) -> str:
    return "\n\n".join(
        f"Level {i + 1} — {level.concept}:\n{level.transcript}"
        for i, level in enumerate(levels)
    )


def _parse_json(raw: str) -> dict:
    """Strip markdown fences Gemini sometimes wraps around JSON responses."""
    cleaned = re.sub(r"^```json\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.IGNORECASE)
    return json.loads(cleaned.strip())


from features.posthog.config.posthog_client import ENV


async def score_assignment(
    data: AssignmentScoreRequest,
    user_id: str = None,
    trace_id: str = None,
) -> AssignmentScoreResponse:
    day_context = _build_day_context(data.levels)
    role_context = get_role_context(data.role.value)
    system_instruction = build_scoring_prompt(
        assignment_prompt=data.assignment_prompt,
        user_response=data.user_response,
        day_context=day_context,
        role=data.role.value,
        role_context=role_context,
        day_number=data.day_number,
    )
    raw = await generate(
        system_instruction=system_instruction,
        user_text="Score this response.",
        temperature=0,  # deterministic — no creative variance in grading
        posthog_distinct_id=user_id,
        posthog_trace_id=trace_id,
        posthog_properties={
            "feature": "assignment_score",
            "env": ENV,
            "day_number": data.day_number,
        },
    )
    parsed = _parse_json(raw)
    return AssignmentScoreResponse(
        score=parsed["score"],
        feedback=parsed["feedback"],
        passed=parsed["passed"],
        breakdown=ScoreBreakdown(
            topic_relevance=parsed["breakdown"]["topicRelevance"],
            concept_application=parsed["breakdown"]["conceptApplication"],
            prompt_quality=parsed["breakdown"]["promptQuality"],
            role_aptitude=parsed["breakdown"]["roleAptitude"],
        ),
        weaknesses=parsed.get("weaknesses", []),
        conversation_id=trace_id,
    )

