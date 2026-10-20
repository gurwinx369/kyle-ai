from schemas.doubt import DoubtRequest
from core.gemini_client import generate
from core.config import DEFAULT_THINKING_BUDGET, GEMINI_FAST_MODEL, GEMINI_DEEP_MODEL
from utils.prompts.role_context import get_role_context
from utils.prompts.system_prompts import build_doubt_prompt, build_general_doubt_prompt
from schemas.common import ModeEnum

_BLOCKED_PHRASES = [
    "write code", "write a code", "give me code", "full code", "complete code",
    "solve this", "solution for", "debug this", "fix this code", "build an app",
    "create a full project", "leetcode", "hackerrank", "assignment answer",
    "copy paste solution",
]

_GENERAL_GREETINGS = {"hi", "hello", "hey", "hi buddy", "hello kibo", "hello kyle"}

_CONTEXTUAL_GREETINGS = {
    "hi", "hello", "hey", "hi buddy", "hello kibo", "hello kyle", "good morning", "good evening"
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
            "Hey 👋 I'm Kibo. Roadmaps, concepts, focus, study strategy — that's my lane. "
            "What are you working on?"
        )

    if any(
        phrase in q
        for phrase in [
            "who are you", "what is kibo", "who made you",
            "whom do you belong to", "what can you do", "whom you belong to",
        ]
    ):
        return (
            "I'm Kibo, Ignitio's AI tutor. I'm here to help you figure out what to learn, "
            "keep you from falling into tutorial hell, and actually make progress. "
            "Hints and explanations — not full code solutions."
        )

    if "what is ignitio" in q or "tell me about ignitio" in q:
        return (
            "Ignitio is a structured learning platform for college students — roadmaps, "
            "progress tracking, quizzes, assignments, and AI guidance. "
            "Kibo is the AI tutor inside it. That's me."
        )

    dangerous = ["how to make a gun", "weapon making", "bomb", "hacking someone", "illegal activity"]
    if any(phrase in q for phrase in dangerous):
        return (
            "I can't help with that. I'm here for learning, roadmaps, concepts, "
            "and technical education inside Ignitio."
        )

    return None


def _get_static_contextual_response(question: str, concept: str | None) -> str | None:
    q = question.lower().strip().rstrip("?!.")

    if q in _CONTEXTUAL_GREETINGS:
        if concept:
            return f'Hey. Working on "{concept}" — what part isn\'t clicking?'
        return "Hey. What part of this lesson isn't clicking? Ask me and I'll break it down."

    if any(
        phrase in q
        for phrase in ["who are you", "what is kibo", "what can you do", "who made you"]
    ):
        if concept:
            return (
                f"I'm Kibo. In this lesson I can help you understand \"{concept}\" "
                f"— ask me what part isn't making sense."
            )
        return "I'm Kibo, Ignitio's AI tutor. In this lesson, I can help clear doubts and guide you with hints."

    return None


from features.posthog.config.posthog_client import ENV

_COMPLEX_KEYWORDS = {
    "optimize", "optimization", "time complexity", "space complexity",
    "recurrence", "dynamic programming", "dp", "memoization", "backtracking",
    "binary search tree", "avl", "red black", "graph", "dijkstra", "segment tree",
    "tle", "time limit exceeded", "memory limit", "stack overflow", "corner case",
    "edge case", "proof", "prove", "step by step", "trace", "why does my code fail",
    "heap", "trie", "shortest path", "topological sort", "divide and conquer",
}


def is_tough_topic(question: str, concept: str | None = None) -> bool:
    text = f"{question} {concept or ''}".lower()
    if any(kw in text for kw in _COMPLEX_KEYWORDS):
        return True
    if text.count("\n") >= 2 and any(token in text for token in ["def ", "class ", "return ", "{", ";", "for (", "while ("]):
        return True
    if len(question) > 180:
        return True
    return False


async def answer_doubt(data: DoubtRequest, user_id: str = None, trace_id: str = None) -> str:
    is_general = data.mode == ModeEnum.general or not data.concept

    if is_general:
        static = _get_static_general_response(data.question)
        if static:
            return static
        if _is_disallowed_general_request(data.question):
            return (
                "That's outside what I do here. I can walk you through the logic, "
                "break the problem into steps, or give a hint you can actually build on. "
                "Want to try that instead?"
            )
    else:
        static = _get_static_contextual_response(data.question, data.concept)
        if static:
            return static

    role_context = get_role_context(data.role.value)
    system_instruction = (
        build_general_doubt_prompt(role_context, data.pageContext or "")
        if is_general
        else build_doubt_prompt(data.concept, data.transcript, role_context, data.pageContext or "")
    )

    history_dicts = [{"role": msg.role, "text": msg.text} for msg in data.history] if data.history else []

    is_deep = is_tough_topic(data.question, data.concept)
    target_model = GEMINI_DEEP_MODEL if is_deep else GEMINI_FAST_MODEL
    thinking_budget = DEFAULT_THINKING_BUDGET if is_deep else None

    return await generate(
        system_instruction=system_instruction,
        user_text=data.question,
        temperature=0.7,
        history=history_dicts,
        model=target_model,
        posthog_distinct_id=user_id,
        posthog_trace_id=trace_id,
        thinking_budget=thinking_budget,
        posthog_properties={
            "feature": "doubt_solving",
            "env": ENV,
            "mode": "general" if is_general else "contextual",
            "deep_reasoning": is_deep,
            "model_assigned": target_model,
            "thinking_budget": thinking_budget or 0,
        },
    )

