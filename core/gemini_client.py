import asyncio
import random

from google import genai
from google.genai import types

from core.config import GEMINI_API_KEY, GEMINI_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)


def _is_transient(err: Exception) -> bool:
    msg = str(err).lower()
    return (
        "503" in msg
        or "service unavailable" in msg
        or "high demand" in msg
        or "try again" in msg
    )


async def generate(system_instruction: str, user_text: str, temperature: float = 0.7) -> str:
    """
    Send a single-turn generation request to Gemini.
    Runs the blocking SDK call in a thread pool to avoid blocking the event loop.
    On a transient 503, retries once after a short random delay (700–1200 ms).
    """
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
    )

    def _call() -> str:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_text,
            config=config,
        )
        return response.text.strip()

    try:
        return await asyncio.to_thread(_call)
    except Exception as err:
        if not _is_transient(err):
            raise
        await asyncio.sleep(random.uniform(0.7, 1.2))
        return await asyncio.to_thread(_call)
