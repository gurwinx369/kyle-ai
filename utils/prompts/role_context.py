# Role context map — injects college-student-aware framing into every Kibo prompt.
# Add a new role by adding one entry to _ROLE_CONTEXTS. Nothing else changes.

_ROLE_CONTEXTS: dict[str, str] = {
    "student": (
        "The learner is a college student. Use examples that feel familiar — studying for a test, "
        "managing a chaotic schedule, finishing something between classes. Be practical and direct."
    ),
    "developer": (
        "The learner is building developer skills. Use beginner-friendly coding examples — "
        "writing a small script, fixing an obvious mistake, trying a new tool for the first time. "
        "Don't assume they know more than the current lesson."
    ),
    "writer": (
        "The learner is building writing skills. Use examples they already understand — "
        "drafting an email, editing a paragraph to be clearer, rewriting something that sounds off. "
        "Keep it practical and grounded."
    ),
    "designer": (
        "The learner is building design skills. Use accessible examples — picking colours, "
        "arranging a simple layout, explaining a design decision to someone else. "
        "Don't assume prior design theory knowledge."
    ),
    "other": (
        "The learner hasn't selected a specific role. Explain concepts clearly, "
        "avoid profession-specific assumptions, use practical examples, and "
        "offer guidance that anyone could apply."
    ),
}

_FALLBACK = "student"


def get_role_context(role: str) -> str:
    return _ROLE_CONTEXTS.get(role, _ROLE_CONTEXTS[_FALLBACK])
