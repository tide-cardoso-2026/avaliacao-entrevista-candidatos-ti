"""Estatisticas por avaliador humano ou sistema (tendencia leniente/rigorosa)."""

from __future__ import annotations

import statistics

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.db.models import ScorecardSnapshot
from app.db.session import get_session_factory


class EvaluatorStats(BaseModel):

    model_config = ConfigDict(extra="forbid")

    evaluatorId: str
    sampleSize: int
    avgScore: float
    deviationFromGlobal: float
    biasLabel: str


# Media global e por avaliador (snapshots de scorecard).
def evaluator_stats(evaluator_id: str) -> EvaluatorStats | None:
    factory = get_session_factory()
    session = factory()
    try:
        all_rows = session.scalars(select(ScorecardSnapshot)).all()
        if not all_rows:
            return None
        global_avg = statistics.mean(r.final_score for r in all_rows)
        mine = [r for r in all_rows if r.evaluator_id == evaluator_id]
        if not mine:
            return None
        avg = statistics.mean(r.final_score for r in mine)
        dev = round(avg - global_avg, 3)
        if dev > 0.35:
            label = "lenient"
        elif dev < -0.35:
            label = "strict"
        else:
            label = "neutral"
        return EvaluatorStats(
            evaluatorId=evaluator_id,
            sampleSize=len(mine),
            avgScore=round(avg, 3),
            deviationFromGlobal=dev,
            biasLabel=label,
        )
    finally:
        session.close()
