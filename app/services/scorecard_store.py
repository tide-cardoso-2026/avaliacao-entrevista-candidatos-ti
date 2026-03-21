"""Persistencia de scorecards estruturados (SQLite)."""

from __future__ import annotations

import json
import logging

from sqlalchemy import select

from app.db.models import ScorecardSnapshot
from app.db.session import get_session_factory
from app.models.scorecard_models import Scorecard

log = logging.getLogger(__name__)


# Grava um scorecard completo (JSON) para ranking e gap analysis.
def save_scorecard_snapshot(
    scorecard: Scorecard,
    *,
    role_slug: str | None = None,
) -> int:
    factory = get_session_factory()
    session = factory()
    try:
        row = ScorecardSnapshot(
            candidate_id=scorecard.candidateId,
            evaluator_id=scorecard.evaluatorId,
            role_slug=role_slug,
            final_score=scorecard.finalScore,
            recommendation=scorecard.recommendation,
            payload_json=scorecard.model_dump_json(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        log.info("Scorecard saved id=%s candidate=%s", row.id, scorecard.candidateId)
        return row.id
    finally:
        session.close()


# Ultimo scorecard persistido para o candidato, se existir.
def get_latest_scorecard(candidate_id: str) -> Scorecard | None:
    factory = get_session_factory()
    session = factory()
    try:
        stmt = (
            select(ScorecardSnapshot)
            .where(ScorecardSnapshot.candidate_id == candidate_id)
            .order_by(ScorecardSnapshot.created_at.desc())
            .limit(1)
        )
        row = session.scalars(stmt).first()
        if not row:
            return None
        data = json.loads(row.payload_json)
        return Scorecard.model_validate(data)
    finally:
        session.close()
