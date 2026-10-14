import asyncio
import random
import uuid

from google.genai import types
from google.genai.errors import APIError

from core.config import GEMINI_API_KEYS, GEMINI_MODEL
from features.posthog.config.posthog_client import get_posthog_client

_current_key_index = 0


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
    Rotates through available API keys if a rate limit error (429/RESOURCE_EXHAUSTED) is hit.
    """
    global _current_key_index

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
    )

    start_index = _current_key_index
    num_keys = len(GEMINI_API_KEYS)

    # ponytail: trace_id defaulted here so callers don't have to import uuid
    _trace_id = posthog_trace_id or str(uuid.uuid4())

    for attempt in range(num_keys):
        key_index = (start_index + attempt) % num_keys
        client = get_posthog_client(key_index)

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

            ph_kwargs = {}
            if posthog_distinct_id:
                ph_kwargs["posthog_distinct_id"] = posthog_distinct_id
                ph_kwargs["posthog_trace_id"] = _trace_id
            if posthog_properties:
                ph_kwargs["posthog_properties"] = posthog_properties

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
                **ph_kwargs,
            )
            text = response.text
            if not text or not text.strip():
                finish_reason = None
                try:
                    finish_reason = response.candidates[0].finish_reason
                except (IndexError, AttributeError):
                    pass
                raise ValueError(
                    f"Gemini returned empty content (finish_reason={finish_reason!r}). "
                    "This is likely a safety filter block or empty candidate."
                )
            return text.strip()

        try:
            result = await asyncio.to_thread(_call)
            _current_key_index = key_index
            return result
        except Exception as err:
            # On transient 503, retry once on the same key
            if _is_transient(err):
                try:
                    await asyncio.sleep(random.uniform(0.7, 1.2))
                    result = await asyncio.to_thread(_call)
                    _current_key_index = key_index
                    return result
                except Exception as retry_err:
                    err = retry_err

            # Inspect the final error for rate limiting
            if not _is_rate_limit_error(err):
                raise err

            next_index = (key_index + 1) % num_keys
            has_next_key = next_index != start_index or attempt < num_keys - 1

            if has_next_key and attempt < num_keys - 1:
                _current_key_index = next_index
            else:
                raise RuntimeError(
                    f"All {num_keys} Gemini API key(s) hit rate limits. Please wait before retrying."
                ) from err
