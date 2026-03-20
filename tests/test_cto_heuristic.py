"""Heurística baseline do CTO (score + risco crítico)."""

from app.core.cto_heuristic import heuristic_final_indication
from app.models.schemas import CTORiskItem, FinalIndication


def test_heuristic_approve_high_score_no_critical_risk():
    r = heuristic_final_indication(8.0, [])
    assert r == FinalIndication.Aprovar


def test_heuristic_reject_critical_risk_even_high_score():
    risks = [CTORiskItem(description="x", impact="alto", probability="alta")]
    r = heuristic_final_indication(8.0, risks)
    assert r == FinalIndication.AprovarComRessalvas


def test_heuristic_ressalvas_mid_score():
    r = heuristic_final_indication(6.5, [])
    assert r == FinalIndication.AprovarComRessalvas


def test_heuristic_reprovar_low_score():
    r = heuristic_final_indication(5.0, [])
    assert r == FinalIndication.Reprovar
