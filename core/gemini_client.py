import asyncio
import logging
import random
import uuid

from google.genai import types
from google.genai.errors import APIError

from core.config import (
    GEMINI_API_KEYS,
    GEMINI_FAST_MODEL,
    GEMINI_DEEP_MODEL,
    GEMINI_MODEL,
    GEMINI_FALLBACK_MODEL,
)
from features.posthog.config.posthog_client import get_posthog_client, posthog

logger = logging.getLogger(__name__)

_current_key_index = 0


def _capture_exception(
    err: Exception,
    distinct_id: str = "anonymous",
    trace_id: str = "",
    properties: dict = None,
) -> None:
    """Send LLM failure / safety exception to PostHog error tracking without crashing."""
    try:
        if posthog and not getattr(posthog, "disabled", False):
            posthog.capture_exception(
                err,
                distinct_id=distinct_id or "anonymous",
                properties={
                    "trace_id": trace_id,
                    "llm_call": True,
                    "model": GEMINI_MODEL,
                    **(properties or {}),
                },
            )
    except Exception:
        pass


def _is_transient(err: Exception) -> bool:
    msg = str(err).lower()
    return (
        "503" in msg
        or "service unavailable" in msg
        or "high demand" in msg
        or "try again" in msg
    )


def _is_rate_limit_error(err: Exception) -> bool:
    if not isinstance(err, APIError):
        msg = str(err).lower()
        return "429" in msg or "resource_exhausted" in msg or "quota" in msg

    if err.code in (429, "429"):
        return True

    status = getattr(err, "status", None)
    if status in (429, "429", "RESOURCE_EXHAUSTED"):
        return True

    msg = (err.message or "").lower()
    return "429" in msg or "resource_exhausted" in msg or "quota" in msg


def _is_auth_error(err: Exception) -> bool:
    msg = str(err).lower()
    return (
        "401" in msg
        or "unauthenticated" in msg
        or "api_key_invalid" in msg
        or "api key not valid" in msg
    )


def _is_daily_quota_exhausted(err: Exception) -> bool:
    msg = str(err).lower()
    return "free_tier_requests" in msg or "quota exceeded" in msg or "retry in" in msg


def _is_retryable_error(err: Exception) -> bool:
    return _is_rate_limit_error(err) or _is_transient(err) or _is_auth_error(err)


async def generate(
    system_instruction: str,
    user_text: str,
    temperature: float = 0.7,
    history: list = None,
    posthog_distinct_id: str = None,
    posthog_trace_id: str = None,
    posthog_properties: dict = None,
    thinking_budget: int | None = None,
    model: str | None = None,
) -> str:
    """
    Send a generation request to Gemini, optionally with multi-turn history.
    Runs the blocking SDK call in a thread pool to avoid blocking the event loop.
    Rotates through available API keys if a rate limit error (429) or transient error (503) is hit.
    Supports dynamic thinking_budget for Deep Reasoning (CoT) and auto-fallback to GEMINI_FALLBACK_MODEL
    if the primary model encounters high-demand 503 spikes or daily quota limits.
    """
    global _current_key_index

    config_kwargs = {
        "system_instruction": system_instruction,
        "temperature": temperature,
    }
    if thinking_budget is not None and thinking_budget > 0:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)

    config = types.GenerateContentConfig(**config_kwargs)

    start_index = _current_key_index
    num_keys = len(GEMINI_API_KEYS)

    _trace_id = posthog_trace_id or str(uuid.uuid4())
    _distinct_id = posthog_distinct_id or "anonymous"

    primary_model = model or GEMINI_FAST_MODEL

    async def _execute_attempt(target_model: str, current_config: types.GenerateContentConfig) -> str:
        nonlocal start_index
        global _current_key_index

        last_err = None
        for attempt in range(num_keys):
            key_index = (start_index + attempt) % num_keys
            client = get_posthog_client(key_index)

            call_properties = dict(posthog_properties or {})
            if attempt > 0:
                call_properties["retry"] = True
            if thinking_budget:
                call_properties["thinking_budget"] = thinking_budget

            def _call() -> str:
                contents = []
                if history:
                    for msg in history:
                        role = msg.get("role", "user")
                        text = msg.get("text", "")
                        contents.append(
                            types.Content(
                                role=role,
                                parts=[types.Part.from_text(text=text)]
                            )
                        )
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=user_text)]
                    )
                )

                response = client.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=current_config,
                    posthog_distinct_id=_distinct_id,
                    posthog_trace_id=_trace_id,
                    posthog_properties=call_properties,
                )
                text = response.text
                if not text or not text.strip():
                    finish_reason = None
                    try:
                        finish_reason = response.candidates[0].finish_reason
                    except (IndexError, AttributeError):
                        pass
                    empty_err = ValueError(
                        f"Gemini returned empty content (finish_reason={finish_reason!r}). "
                        "This is likely a safety filter block or empty candidate."
                    )
                    _capture_exception(
                        empty_err,
                        distinct_id=_distinct_id,
                        trace_id=_trace_id,
                        properties={**call_properties, "finish_reason": str(finish_reason)},
                    )
                    raise empty_err
                return text.strip()

            try:
                result = await asyncio.to_thread(_call)
                _current_key_index = key_index
                return result
            except Exception as err:
                last_err = err
                if _is_transient(err):
                    try:
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        result = await asyncio.to_thread(_call)
                        _current_key_index = key_index
                        return result
                    except Exception as retry_err:
                        last_err = retry_err

                if not _is_retryable_error(last_err):
                    _capture_exception(
                        last_err,
                        distinct_id=_distinct_id,
                        trace_id=_trace_id,
                        properties=call_properties,
                    )
                    raise last_err

                # Fast-circuit break if daily free tier quota is depleted
                if _is_daily_quota_exhausted(last_err):
                    logger.warning(
                        "[gemini_client] Daily quota for %s exhausted on key %d (%s). Circuit-breaking key rotation.",
                        target_model,
                        key_index,
                        last_err,
                    )
                    break

                if _is_auth_error(last_err):
                    logger.warning(
                        "[gemini_client] API key at index %d failed auth. Rotating.",
                        key_index,
                    )

                next_index = (key_index + 1) % num_keys
                if next_index != start_index or attempt < num_keys - 1:
                    _current_key_index = next_index

        raise last_err

    # 1. Primary execution on primary_model
    try:
        return await _execute_attempt(primary_model, config)
    except Exception as primary_err:
        # If primary failed due to 503 / high demand / quota, fallback to GEMINI_FALLBACK_MODEL
        if GEMINI_FALLBACK_MODEL and GEMINI_FALLBACK_MODEL != primary_model and _is_retryable_error(primary_err):
            logger.warning(
                "[gemini_client] Primary model %s failed (%s). Executing graceful fallback to %s.",
                primary_model,
                primary_err,
                GEMINI_FALLBACK_MODEL,
            )
            fallback_config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            )
            try:
                return await _execute_attempt(GEMINI_FALLBACK_MODEL, fallback_config)
            except Exception as fallback_err:
                primary_err = fallback_err

        exhausted_err = RuntimeError(
            f"All Gemini API key(s) failed on {primary_model} and fallback {GEMINI_FALLBACK_MODEL}."
        )
        _capture_exception(
            exhausted_err,
            distinct_id=_distinct_id,
            trace_id=_trace_id,
            properties={"failure_reason": "exhausted_pool_limits_or_auth"},
        )
        raise exhausted_err from primary_err

