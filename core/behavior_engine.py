"""
behavior_engine.py — the ONLY place grading/classification math lives.
Pure functions, no DB access, no side effects — matches the stateless
FastAPI service design. Next.js supplies all state (prior attempts, E_i
stats) on every call and persists whatever comes back.

Ported unchanged from the verified reference (behavior_formula_verify.py) —
same branch order, same likelihood table, same strict fast+correct-only
luck-check. The only addition is compute_e_i_incremental, which is
mathematically identical to the batch shrinkage formula, just reformulated
so callers don't need to pass a full observed-times list — only the
current blended value and how many samples produced it.
"""

import math

MANUAL_ANCHORS_MS = {"easy": 12000, "medium": 20000, "hard": 32000}
SHRINK_W = 10

LIKELIHOOD = {
    "FAST":   {"knows_correct": 0.55, "knows_wrong": 0.15, "guess_correct": 0.50, "guess_wrong": 0.45},
    "MEDIUM": {"knows_correct": 0.35, "knows_wrong": 0.35, "guess_correct": 0.30, "guess_wrong": 0.30},
    "SLOW":   {"knows_correct": 0.08, "knows_wrong": 0.35, "guess_correct": 0.15, "guess_wrong": 0.15},
    "GRACE":  {"knows_correct": 0.02, "knows_wrong": 0.15, "guess_correct": 0.05, "guess_wrong": 0.10},
}
P_CORRECT_KNOWS = 0.92
P_WRONG_KNOWS = 0.08


# ============================================================
# LAYER 0 — E_i, incremental form
# ============================================================
def compute_e_i_incremental(ei_current, sample_count, difficulty_tier, new_observed_ms=None):
    """
    ei_current / sample_count: None / 0 on true cold start (Next.js has
    never stored a value for this concept+tier yet).
    If new_observed_ms is None, this just resolves the current E_i to use
    for grading (no update). If provided, returns the updated (e_i, n)
    pair for Next.js to persist.

    Identical math to E_i(n) = (w*anchor + sum(observed))/(w+n) applied
    incrementally — verified equivalent for n=0,1,2... in isolation.
    """
    anchor = MANUAL_ANCHORS_MS[difficulty_tier]
    if ei_current is None or sample_count == 0:
        ei_current = anchor
        sample_count = 0

    if new_observed_ms is None:
        return ei_current, sample_count

    ei_new = (ei_current * (SHRINK_W + sample_count) + new_observed_ms) / (SHRINK_W + sample_count + 1)
    return ei_new, sample_count + 1


# ============================================================
# LAYER 1 — per-attempt grading (UNCHANGED from verified reference)
# ============================================================
def speed_bucket(t_i_ms, r_i):
    if t_i_ms > 70000:
        return "UNATTEMPTED"
    if t_i_ms >= 60000:
        return "GRACE"
    if r_i <= 0.5:
        return "FAST"
    if r_i <= 1.3:
        return "MEDIUM"
    return "SLOW"


def confidence_from_latency(r_i, bucket, k=2):
    c_i = 1 / (1 + r_i ** k)
    if bucket == "GRACE":
        c_i = min(c_i, 0.15)
    return c_i


def grade_attempt(t_i_ms, e_i_ms, was_correct, n_options, model_version="v1"):
    r_i = t_i_ms / e_i_ms
    bucket = speed_bucket(t_i_ms, r_i)

    result = {
        "r_i": r_i, "speedBucket": bucket, "wasCorrect": was_correct,
        "nOptions": n_options, "modelVersion": model_version,
        "responseTimeMs": t_i_ms,
        "rgbFlag": t_i_ms < max(3000, 0.10 * e_i_ms),
    }

    if bucket == "UNATTEMPTED":
        result["c_i"] = None
        result["llrContribution"] = None
        return result

    result["c_i"] = confidence_from_latency(r_i, bucket)

    p_correct_guess = 1 / n_options
    p_wrong_guess = 1 - p_correct_guess

    if was_correct:
        p_knows = LIKELIHOOD[bucket]["knows_correct"] * P_CORRECT_KNOWS
        p_guess = LIKELIHOOD[bucket]["guess_correct"] * p_correct_guess
    else:
        p_knows = LIKELIHOOD[bucket]["knows_wrong"] * P_WRONG_KNOWS
        p_guess = LIKELIHOOD[bucket]["guess_wrong"] * p_wrong_guess

    result["llrContribution"] = math.log(p_knows / p_guess)
    return result


# ============================================================
# LAYER 2 — concept classification (UNCHANGED from verified reference)
# ============================================================
def classify_concept(attempts):
    attempted = [a for a in attempts if a["speedBucket"] != "UNATTEMPTED"]
    n = len(attempted)

    if n < 3:
        return {"verdict": "INSUFFICIENT_DATA", "nAttempts": n}

    rgb_count = sum(1 for a in attempted if a["rgbFlag"])
    if rgb_count / n >= 2 / 3:
        return {"verdict": "DISENGAGED_GUESSING", "nAttempts": n, "rgbCount": rgb_count}

    llr_total = sum(a["llrContribution"] for a in attempted)
    posterior = 1 / (1 + math.exp(-llr_total))

    fast_correct = [a for a in attempted if a["speedBucket"] == "FAST" and a["wasCorrect"]]
    if fast_correct:
        p_chance = 1.0
        for a in fast_correct:
            p_chance *= 1 / a["nOptions"]
        binomial_rejects_luck = p_chance < 0.05
    else:
        p_chance = None
        binomial_rejects_luck = True

    wrong = [a for a in attempted if not a["wasCorrect"]]
    majority_wrong_slow_grace = (
        len(wrong) > 0 and
        sum(1 for a in wrong if a["speedBucket"] in ("SLOW", "GRACE")) / len(wrong) > 0.5
    )

    if posterior >= 0.75 and binomial_rejects_luck:
        verdict = "MASTERY"
    elif posterior <= 0.25 and majority_wrong_slow_grace:
        verdict = "KNOWLEDGE_GAP"
    else:
        verdict = "DEVELOPING"

    return {
        "verdict": verdict, "nAttempts": n, "posterior": round(posterior, 4),
        "llr_total": round(llr_total, 4), "pChance": p_chance, "rgbCount": rgb_count,
    }