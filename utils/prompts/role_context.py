# Role context map — injects beginner-safe framing into every Kyle prompt.
# Add a new role by adding one entry to _ROLE_CONTEXTS. Nothing else changes.

_ROLE_CONTEXTS: dict[str, str] = {
    "student": (
        "Use examples from everyday school life — like preparing for a test, "
        "writing class notes, or finishing an assignment."
    ),
    "developer": (
        "Use simple, beginner-friendly coding examples — like writing a small script, "
        "fixing a mistake in code, or trying a new tool for the first time."
    ),
    "writer": (
        "Use writing examples most people already understand — like drafting an email, "
        "editing a blog post, or rewriting a sentence to sound clearer."
    ),
    "designer": (
        "Use design examples a beginner would recognise — like picking a colour for a "
        "poster, arranging a simple page layout, or explaining a design idea to a friend."
    ),
    "other": (
        "The learner has not selected a specific professional role. Explain concepts "
        "clearly, avoid profession-specific assumptions, use practical examples, and "
        "offer adaptable guidance."
    ),
}

_FALLBACK = "student"


def get_role_context(role: str) -> str:
    return _ROLE_CONTEXTS.get(role, _ROLE_CONTEXTS[_FALLBACK])
