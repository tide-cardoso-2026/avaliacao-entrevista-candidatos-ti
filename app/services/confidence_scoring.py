"""Confidence 0-1 baseado em sinais objetivos (clareza, evidencia, consistencia parcial)."""

from __future__ import annotations

from app.models.scorecard_models import ConfidenceScore


# Heuristica deterministica; fatores explicam o valor para auditoria.
def build_confidence(
    *,
    answer_text: str,
    justification: str,
    signals: list[str],
    weaknesses: list[str],
    anti_patterns: list[str],
) -> ConfidenceScore:
    factors: list[str] = []
    v = 0.25

    alen = len(answer_text.strip())
    if alen >= 80:
        factors.append("answer_substantive")
        v += 0.2
    elif alen >= 40:
        factors.append("answer_moderate")
        v += 0.12

    jlen = len(justification.strip())
    if jlen >= 60:
        factors.append("justification_grounded_long")
        v += 0.15
    elif jlen >= 40:
        factors.append("justification_adequate")
        v += 0.08

    if len(signals) >= 3:
        factors.append("multiple_extracted_signals")
        v += 0.12
    elif len(signals) >= 1:
        factors.append("some_signals")
        v += 0.06

    if weaknesses:
        factors.append("weaknesses_identified")
        v += 0.05

    if anti_patterns:
        factors.append("anti_patterns_flagged")
        v -= 0.08

    v = max(0.05, min(1.0, v))
    return ConfidenceScore(value=round(v, 3), factors=factors)
