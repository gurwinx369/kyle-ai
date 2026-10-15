import asyncio
import random
import uuid

from google.genai import types
from google.genai.errors import APIError

from core.config import GEMINI_API_KEYS, GEMINI_MODEL
from features.posthog.config.posthog_client import get_posthog_client, posthog

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


def _is_retryable_error(err: Exception) -> bool:
    return _is_rate_limit_error(err) or _is_transient(err)


async def generate(
    system_instruction: str,
    user_text: str,
    temperature: float = 0.7,
    history: list = None,
    posthog_distinct_id: str = None,
    posthog_trace_id: str = None,
    posthog_properties: dict = None,
) -> str:
    """
    Send a generation request to Gemini, optionally with multi-turn history.
    Runs the blocking SDK call in a thread pool to avoid blocking the event loop.
    Rotates through available API keys if a rate limit error (429) or transient error (503) is hit.
    """
    global _current_key_index

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
    )

    start_index = _current_key_index
    num_keys = len(GEMINI_API_KEYS)

    _trace_id = posthog_trace_id or str(uuid.uuid4())
    _distinct_id = posthog_distinct_id or "anonymous"

    for attempt in range(num_keys):
        key_index = (start_index + attempt) % num_keys
        client = get_posthog_client(key_index)

        # Tag retry attempts so PostHog analytics does not double-count retries as genuine new usage
        call_properties = dict(posthog_properties or {})
        if attempt > 0:
            call_properties["retry"] = True

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
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
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
            # On transient 503, retry once on the same key with brief jitter
            if _is_transient(err):
                try:
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    result = await asyncio.to_thread(_call)
                    _current_key_index = key_index
                    return result
                except Exception as retry_err:
                    err = retry_err

            # Inspect if error is retryable across remaining keys
            if not _is_retryable_error(err):
                _capture_exception(
                    err,
                    distinct_id=_distinct_id,
                    trace_id=_trace_id,
                    properties=call_properties,
                )
                raise err

            next_index = (key_index + 1) % num_keys
            has_next_key = next_index != start_index or attempt < num_keys - 1

            if has_next_key and attempt < num_keys - 1:
                _current_key_index = next_index
            else:
                exhausted_err = RuntimeError(
                    f"All {num_keys} Gemini API key(s) failed due to rate limits or temporary high demand. Please try again shortly."
                )
                _capture_exception(
                    exhausted_err,
                    distinct_id=_distinct_id,
                    trace_id=_trace_id,
                    properties={**call_properties, "failure_reason": "exhausted_pool_limits_or_transient"},
                )
                raise exhausted_err from err

