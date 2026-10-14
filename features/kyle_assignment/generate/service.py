from core.gemini_client import generate
from schemas.assignment import AssignmentGenerateRequest
from utils.prompts.role_context import get_role_context
from utils.prompts.system_prompts import build_assignment_prompt


def _build_day_context(levels: list) -> str:
    """Combines all level contexts into one block — mirrors buildDayContext in JS."""
    return "\n\n".join(
        f"Level {i + 1} — {level.concept}:\n{level.transcript}"
        for i, level in enumerate(levels)
    )


from features.posthog.config.posthog_client import ENV


async def generate_assignment(
    data: AssignmentGenerateRequest,
    user_id: str = None,
    trace_id: str = None,
) -> str:
    day_context = _build_day_context(data.levels)
    role_context = get_role_context(data.role.value)
    system_instruction = build_assignment_prompt(
        day_context=day_context,
        role=data.role.value,
        role_context=role_context,
        day_number=data.day_number,
    )
    return await generate(
        system_instruction=system_instruction,
        user_text=f"Generate the Day {data.day_number} assignment.",
        temperature=0.7,
        posthog_distinct_id=user_id,
        posthog_trace_id=trace_id,
        posthog_properties={
            "feature": "assignment_generate",
            "env": ENV,
            "day_number": data.day_number,
        },
    )

