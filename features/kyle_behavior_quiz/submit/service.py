from schemas.behavior_quiz import (
    GradeSessionRequest, GradeSessionResponse, GradedAttemptOut,
    ConceptVerdictOut, EiStats
)
from core.behavior_engine import grade_attempt, classify_concept, compute_e_i_incremental

def grade_session_service(req: GradeSessionRequest) -> GradeSessionResponse:
    graded_attempts = []
    updated_ei_stats = {}
    attempts_by_concept = {}

    for sub in req.submittedAttempts:
        was_correct = sub.selectedOption == sub.correctOption

        graded = grade_attempt(
            t_i_ms=sub.responseTimeMs,
            e_i_ms=sub.eiSnapshot,
            was_correct=was_correct,
            n_options=sub.nOptions,
            model_version=sub.modelVersion,
        )

        graded_attempts.append(GradedAttemptOut(
            concept=sub.concept,
            difficultyTier=sub.difficultyTier,
            wasCorrect=was_correct,
            responseTimeMs=sub.responseTimeMs,
            speedBucket=graded["speedBucket"],
            rgbFlag=graded["rgbFlag"],
            llrContribution=graded["llrContribution"],
            nOptions=sub.nOptions,
            modelVersion=sub.modelVersion,
        ))

        # update E_i for this (concept, tier), only using real observed time
        key = f"{sub.concept}::{sub.difficultyTier}"
        current = req.eiStatsByConceptTier.get(key, EiStats())
        new_e_i, new_n = compute_e_i_incremental(
            current.eiCurrent, current.sampleCount, sub.difficultyTier, sub.responseTimeMs
        )
        updated_ei_stats[key] = EiStats(eiCurrent=new_e_i, sampleCount=new_n)

        attempts_by_concept.setdefault(sub.concept, []).append(graded)

    # pool with prior history (passed in by Next.js) before classifying
    concept_verdicts = {}
    for concept, new_attempts in attempts_by_concept.items():
        prior = req.priorAttemptsByConcept.get(concept, [])
        prior_as_dicts = [p.model_dump() for p in prior]
        pooled = prior_as_dicts + new_attempts
        result = classify_concept(pooled)
        concept_verdicts[concept] = ConceptVerdictOut(**result)

    return GradeSessionResponse(
        gradedAttempts=graded_attempts,
        updatedEiStats=updated_ei_stats,
        conceptVerdicts=concept_verdicts,
    )
