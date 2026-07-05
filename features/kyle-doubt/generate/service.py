from schemas.doubt import DoubtRequest
from core.gemini_client import generate
from utils.prompts.role_context import get_role_context
from utils.prompts.system_prompts import build_doubt_prompt, build_general_doubt_prompt
from schemas.common import ModeEnum

_BLOCKED_PHRASES = [
    "write code", "write a code", "give me code", "full code", "complete code",
    "solve this", "solution for", "debug this", "fix this code", "build an app",
    "create a full project", "leetcode", "hackerrank", "assignment answer",
    "copy paste solution",
]

_GENERAL_GREETINGS = {"hi", "hello", "hey", "hi buddy", "hello kyle"}

_CONTEXTUAL_GREETINGS = {
    "hi", "hello", "hey", "hi buddy", "hello kyle", "good morning", "good evening"
}


def _is_disallowed_general_request(question: str) -> bool:
    q = question.lower()
    if any(phrase in q for phrase in _BLOCKED_PHRASES):
        return True
    # Block large pasted code blocks (> 400 chars with many braces or semicolons)
    if len(q) > 400 and (q.count("{") > 3 or q.count(";") > 3):
        return True
    return False


def _get_static_general_response(question: str) -> str | None:
    q = question.lower().strip().rstrip("?!.")

    if q in _GENERAL_GREETINGS:
        return (
            "Hi, I'm Kyle. I can help you with roadmap guidance, learning focus, "
            "concepts, and study strategy. What are you learning today?"
        )

    if any(
        phrase in q
        for phrase in [
            "who are you", "what is kyle", "who made you",
            "whom do you belong to", "what can you do", "whom you belong to",
        ]
    ):
        return (
            "I'm Kyle, Ignitio's AI mentor. I'm part of the Ignitio learning platform "
            "and I'm here to guide learners with roadmap direction, concepts, focus, and "
            "study strategy. I give hints and explanations, not full code solutions."
        )

    if "what is ignitio" in q or "tell me about ignitio" in q:
        return (
            "Ignitio is a gamified learning platform that helps learners build technical "
            "skills through structured roadmaps, progress tracking, assignments, quizzes, "
            "and AI mentor guidance. Kyle is the AI mentor layer inside Ignitio."
        )

    dangerous = ["how to make a gun", "weapon making", "bomb", "hacking someone", "illegal activity"]
    if any(phrase in q for phrase in dangerous):
        return (
            "I can't help with that. I'm here to support learning, roadmaps, concepts, "
            "focus, and safe technical education inside Ignitio."
        )

    return None


def _get_static_contextual_response(question: str, concept: str | None) -> str | None:
    q = question.lower().strip().rstrip("?!.")

    if q in _CONTEXTUAL_GREETINGS:
        if concept:
            return (
                f'Hey! I\'m here to help with "{concept}." '
                "Ask me what part feels confusing, and I'll explain it simply."
            )
        return "Hey! I'm here to help with this lesson. Ask me what part feels confusing, and I'll explain it simply."

    if any(
        phrase in q
        for phrase in ["who are you", "what is kyle", "what can you do", "who made you"]
    ):
        if concept:
            return (
                f"I'm Kyle, Ignitio's AI mentor. In this lesson, I can help explain "
                f'"{concept}," clear doubts, and guide you with hints.'
            )
        return "I'm Kyle, Ignitio's AI mentor. In this lesson, I can help clear doubts and guide you with hints."

    return None


async def answer_doubt(data: DoubtRequest) -> str:
    is_general = data.mode == ModeEnum.general or not data.concept

    if is_general:
        static = _get_static_general_response(data.question)
        if static:
            return static
        if _is_disallowed_general_request(data.question):
            return (
                "I can't write the full code, debug large blocks, or provide complete "
                "solutions in Global Ask Kyle. I can help you understand the logic, break "
                "the problem into steps, or give a small hint so you can implement it yourself."
            )
    else:
        static = _get_static_contextual_response(data.question, data.concept)
        if static:
            return static

    role_context = get_role_context(data.role.value)
    system_instruction = (
        build_general_doubt_prompt(role_context)
        if is_general
        else build_doubt_prompt(data.concept, data.transcript, role_context)
    )

    return await generate(
        system_instruction=system_instruction,
        user_text=data.question,
        temperature=0.7,
    )
