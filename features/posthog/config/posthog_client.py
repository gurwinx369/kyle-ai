import os
from posthog import Posthog
from posthog.ai.gemini import Client

from core.config import GEMINI_API_KEYS

posthog = Posthog(
    os.getenv("POSTHOG_API_KEY", ""),
    host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
)

# One PostHog-wrapped client per API key, mirroring the rotation pool in gemini_client.py.
# ponytail: lazy-init list mirrors _clients in gemini_client.py — same pattern, no new abstraction.
_ph_clients: list = [None] * len(GEMINI_API_KEYS)


def get_posthog_client(index: int) -> Client:
    if _ph_clients[index] is None:
        _ph_clients[index] = Client(api_key=GEMINI_API_KEYS[index], posthog_client=posthog)
    return _ph_clients[index]