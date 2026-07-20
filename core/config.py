import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEYS: list[str] = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_ONE"),
    os.getenv("GEMINI_API_KEY_TWO"),
    os.getenv("GEMINI_API_KEY_THREE"),
]
GEMINI_API_KEYS = [key for key in GEMINI_API_KEYS if key]

if not GEMINI_API_KEYS:
    raise ValueError("No Gemini API keys configured. Set at least GEMINI_API_KEY in your env.")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_CLIENT_EMAIL: str = os.getenv("FIREBASE_CLIENT_EMAIL")
FIREBASE_PRIVATE_KEY: str = os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n")
