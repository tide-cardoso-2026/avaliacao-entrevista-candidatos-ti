"""Pesos das dimensões de avaliação (scorecard padronizado)."""

from __future__ import annotations

from app.models.scorecard_models import Recommendation

# Pesos devem somar 1.0.
DIMENSION_WEIGHTS: dict[str, float] = {
    "technical": 0.4,
    "architecture": 0.3,
    "product": 0.2,
    "communication": 0.1,
}


# Calcula nota final 1.0–5.0 a partir de subnotas 1–5 por dimensão.
def weighted_dimension_score(
    *,
    technical: float,
    architecture: float,
    product: float,
    communication: float,
) -> float:
    s = (
        technical * DIMENSION_WEIGHTS["technical"]
        + architecture * DIMENSION_WEIGHTS["architecture"]
        + product * DIMENSION_WEIGHTS["product"]
        + communication * DIMENSION_WEIGHTS["communication"]
    )
    return round(s, 3)


# Converte média ponderada (1–5) em recomendação de contratação.
def recommendation_from_final_score(final_score: float) -> Recommendation:
    if final_score >= 4.25:
        return "STRONG_HIRE"
    if final_score >= 3.0:
        return "HIRE"
    return "NO_HIRE"
