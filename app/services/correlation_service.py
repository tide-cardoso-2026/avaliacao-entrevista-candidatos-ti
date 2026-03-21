"""Correlacao entre varias respostas do mesmo candidato (falsa senioridade, variancia)."""

from __future__ import annotations

from app.models.scorecard_models import EvaluateAnswerResponse


# Detecta padroes de inconsistencia entre avaliacoes de respostas distintas.
def correlate_evaluations(responses: list[EvaluateAnswerResponse]) -> dict:
    if not responses:
        return {"flags": [], "detail": "empty"}

    scores: list[float] = []
    levels: list[int] = []

    for r in responses:
        scores.append(float(r.aiScore.score))
        if r.aiScore.seniorityDetail is not None:
            levels.append(int(r.aiScore.seniorityDetail.level))
        else:
            levels.append(int(round(float(r.aiScore.seniorityLevelDetected))))

    flags: list[str] = []
    if levels and scores:
        if max(levels) >= 4 and min(scores) <= 2.5:
            flags.append("INCONSISTENT_PROFILE")
        if max(scores) - min(scores) >= 3.0 and len(scores) >= 2:
            flags.append("HIGH_SCORE_VARIANCE")
        if min(scores) >= 4.0 and any(lv <= 2 for lv in levels):
            flags.append("SENIORITY_SCORE_MISMATCH")

    return {
        "flags": flags,
        "scores": scores,
        "seniorityLevels": levels,
        "n": len(responses),
    }
