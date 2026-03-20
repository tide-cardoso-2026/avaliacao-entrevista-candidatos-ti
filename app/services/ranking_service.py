"""Ranking e percentil entre candidatos da mesma função (role_slug)."""

from __future__ import annotations

from sqlalchemy import select

from app.db.models import ScorecardSnapshot
from app.db.session import get_session_factory
from app.models.scorecard_models import Benchmark, CandidateRanking


# Calcula percentil (0-100): maior nota = percentil mais alto (aproximacao empirica).
def compute_percentiles(final_scores: list[float]) -> dict[float, float]:
    if not final_scores:
        return {}
    sorted_unique = sorted(set(final_scores))
    n = len(final_scores)
    out: dict[float, float] = {}
    if n == 1:
        return {sorted_unique[0]: 100.0}
    for s in sorted_unique:
        below = sum(1 for x in final_scores if x < s)
        out[s] = round(100.0 * below / (n - 1), 2)
    return out


# Lista rankings com percentil para um mesmo papel (ou todos se role_slug None).
def candidate_rankings_for_role(*, role_slug: str | None = None) -> list[CandidateRanking]:
    factory = get_session_factory()
    session = factory()
    try:
        stmt = select(ScorecardSnapshot).order_by(ScorecardSnapshot.created_at.desc())
        rows = session.scalars(stmt).all()
        filtered = [r for r in rows if role_slug is None or (r.role_slug or "") == role_slug]
        # Ultimo scorecard por candidato
        by_candidate: dict[str, ScorecardSnapshot] = {}
        for r in filtered:
            if r.candidate_id not in by_candidate:
                by_candidate[r.candidate_id] = r
        scores = [r.final_score for r in by_candidate.values()]
        pct_map = compute_percentiles(scores)
        result: list[CandidateRanking] = []
        for cid, row in by_candidate.items():
            pct = pct_map.get(row.final_score, 0.0)
            cohort = role_slug or "all_scorecards"
            result.append(
                CandidateRanking(
                    candidateId=cid,
                    finalScore=row.final_score,
                    percentile=pct,
                    benchmark=Benchmark(percentile=pct, comparedTo=cohort),
                )
            )
        result.sort(key=lambda x: x.finalScore, reverse=True)
        return result
    finally:
        session.close()
