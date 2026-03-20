"""Heurística objetiva de indicação final (baseline auditável) vs laudo LLM."""

from __future__ import annotations

from app.models.schemas import CTORiskItem, FinalIndication


def heuristic_final_indication(score_final: float, risks: list[CTORiskItem]) -> FinalIndication:
    """
    Regra simples: score alto sem risco crítico → aprovar;
    score médio → ressalvas; caso contrário reprovar.
    Risco crítico = impacto alto E probabilidade alta simultaneamente.
    """
    high_critical = any(
        r.impact == "alto" and r.probability == "alta" for r in risks
    )
    s = float(score_final)
    if s >= 7.5 and not high_critical:
        return FinalIndication.Aprovar
    if s >= 6.0:
        return FinalIndication.AprovarComRessalvas
    return FinalIndication.Reprovar
