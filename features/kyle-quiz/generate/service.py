import json
import random
import re

from core.gemini_client import generate
from schemas.quiz import QuizGenerateRequest, QuizGenerateResponse, QuizOptions
from utils.prompts.role_context import get_role_context
from utils.prompts.system_prompts import build_quiz_prompt

_OPTION_KEYS = ["A", "B", "C"]


def _parse_json(raw: str) -> dict:
    """Strip markdown fences Gemini sometimes wraps around JSON responses."""
    cleaned = re.sub(r"^```json\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.IGNORECASE)
    return json.loads(cleaned.strip())


def _shuffle_quiz_options(quiz: dict) -> dict:
    """
    Randomises A/B/C option order while updating correctAnswer to the new position.
    Port of shuffleQuizOptions() from kyle.service.js.
    """
    correct_key = str(quiz.get("correctAnswer", "")).strip().upper()[:1]

    if correct_key not in _OPTION_KEYS:
        raise ValueError(f"Invalid quiz correctAnswer: {correct_key!r}")

    items = []
    for key in _OPTION_KEYS:
        text = str(quiz["options"].get(key, "")).strip()
        if not text:
            raise ValueError(f"Quiz option {key!r} is empty")
        items.append({"text": text, "is_correct": key == correct_key})

    random.shuffle(items)

    options: dict[str, str] = {}
    new_correct: str | None = None
    for i, item in enumerate(items):
        new_key = _OPTION_KEYS[i]
        options[new_key] = item["text"]
        if item["is_correct"]:
            new_correct = new_key

    if new_correct is None:
        raise ValueError("Failed to determine shuffled correct answer")

    return {**quiz, "options": options, "correctAnswer": new_correct}


async def generate_quiz(data: QuizGenerateRequest) -> QuizGenerateResponse:
    role_context = get_role_context(data.role.value)
    system_instruction = build_quiz_prompt(
        concept=data.concept,
        transcript=data.transcript,
        role_context=role_context,
    )
    raw = await generate(
        system_instruction=system_instruction,
        user_text="Generate the quiz question.",
        temperature=0,  # deterministic — no random variance in quiz questions
    )
    quiz = _parse_json(raw)
    shuffled = _shuffle_quiz_options(quiz)
    return QuizGenerateResponse(
        question=shuffled["question"],
        options=QuizOptions(**shuffled["options"]),
        correct_answer=shuffled["correctAnswer"],
        explanation=shuffled["explanation"],
    )
