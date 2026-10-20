import time
import logging
from schemas.funfact import FunFactRequest
from core.gemini_client import generate
from core.config import GEMINI_FAST_MODEL
from utils.prompts.role_context import get_role_context
from features.posthog.config.posthog_client import ENV

logger = logging.getLogger(__name__)

# Concept-level in-memory cache: {cache_key: (fun_fact_text, timestamp)}
_FUN_FACT_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL_SECONDS = 86400  # 24 hours


def _get_static_concept_fallback(concept: str) -> str:
    return (
        f"Did you know? Mastering {concept} is one of the core foundational building blocks "
        "used in production systems every single day!"
    )


async def generate_fun_fact(
    request: FunFactRequest,
    user_id: str = None,
    trace_id: str = None,
) -> str:
    concept = (request.concept or "").strip()
    profession = request.user_profession or "student"
    cache_key = f"{concept.lower()}_{profession.lower()}"

    # Check cache first for 0ms instantaneous response
    now = time.time()
    if cache_key in _FUN_FACT_CACHE:
        cached_fact, timestamp = _FUN_FACT_CACHE[cache_key]
        if now - timestamp < _CACHE_TTL_SECONDS:
            return cached_fact

    role_ctx = get_role_context(profession)

    system_prompt = f"""You are Kibo, an AI learning mentor.
{role_ctx}

Your task is to provide a single, punchy, 1-2 sentence fun fact or "did you know" insight about the concept the user is learning.
Do not provide a long explanation. Do not use markdown. Just provide the fun fact.
Make it sound slightly retro, geeky, or encouraging, fitting your persona as a floating pet assistant.

Concept: {concept}
Transcript context:
{request.transcript[:2000]}
"""

    try:
        response = await generate(
            user_text="Provide a fun fact.",
            system_instruction=system_prompt,
            model=GEMINI_FAST_MODEL,
            thinking_budget=None,
            posthog_distinct_id=user_id,
            posthog_trace_id=trace_id,
            posthog_properties={
                "feature": "funfact_generate",
                "env": ENV,
            },
        )
        fact = response.strip()
        if fact:
            _FUN_FACT_CACHE[cache_key] = (fact, now)
            return fact
    except Exception as err:
        logger.warning("[generate_fun_fact] Gemini generation failed: %s. Using static fallback.", err)

    return _get_static_concept_fallback(concept or "this concept")


