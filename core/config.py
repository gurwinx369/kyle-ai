import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def _clean_key(val: str | None) -> str:
    if not val:
        return ""
    return val.strip().strip("'\"")


GEMINI_API_KEY: str = _clean_key(os.getenv("GEMINI_API_KEY"))
GEMINI_API_KEYS: list[str] = [
    _clean_key(os.getenv("GEMINI_API_KEY")),
    _clean_key(os.getenv("GEMINI_API_KEY_ONE")),
    _clean_key(os.getenv("GEMINI_API_KEY_TWO")),
    _clean_key(os.getenv("GEMINI_API_KEY_THREE")),
]
GEMINI_API_KEYS = [key for key in GEMINI_API_KEYS if key]

if not GEMINI_API_KEYS:
    logger.warning("No Gemini API keys configured in environment variables.")

GEMINI_FAST_MODEL: str = os.getenv("GEMINI_FAST_MODEL", "gemini-3.5-flash")
GEMINI_DEEP_MODEL: str = os.getenv("GEMINI_DEEP_MODEL", "gemini-3.8-flash")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", GEMINI_FAST_MODEL)
GEMINI_FALLBACK_MODEL: str = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash")
DEFAULT_THINKING_BUDGET: int = int(os.getenv("DEFAULT_THINKING_BUDGET", "256"))

FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
FIREBASE_CLIENT_EMAIL: str = os.getenv("FIREBASE_CLIENT_EMAIL", "")

_raw_private_key = os.getenv("FIREBASE_PRIVATE_KEY") or ""
FIREBASE_PRIVATE_KEY: str = _raw_private_key.replace("\\n", "\n")

