"""Persistência de execuções e feedback pós-contratação no SQLite (SQLAlchemy)."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select

from app.db.models import EvaluationRun, PerformanceFeedback
from app.db.session import get_session_factory
from app.models.schemas import CTOFinalEvaluation

log = logging.getLogger(__name__)


# Persiste uma execução completa para histórico e calibração futura.
def save_evaluation_run(
    *,
    vaga: str,
    candidato: str,
    client_stem: str | None,
    cto: CTOFinalEvaluation,
    pdf_path: str | None,
    full_payload: dict[str, Any] | None = None,
) -> int:
    factory = get_session_factory()
    session = factory()
    try:
        run = EvaluationRun(
            vaga=vaga,
            candidato=candidato,
            client_stem=client_stem,
            final_score=cto.score_final,
            final_indication=cto.final_indication.value,
            pdf_path=pdf_path,
            payload_json=json.dumps(full_payload, ensure_ascii=False, default=str) if full_payload else None,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        log.debug("History saved: run_id=%s", run.id)
        return run.id
    finally:
        session.close()


# Registra performance real na empresa (para calibrar vs nota do modelo).
def add_performance_feedback(
    *,
    run_id: int,
    hired: bool | None,
    company_performance_score: float | None,
    notes: str | None,
) -> int:
    factory = get_session_factory()
    session = factory()
    try:
        fb = PerformanceFeedback(
            run_id=run_id,
            hired=hired,
            company_performance_score=company_performance_score,
            notes=notes,
        )
        session.add(fb)
        session.commit()
        session.refresh(fb)
        return fb.id
    finally:
        session.close()


# Retorna as últimas linhas de `evaluation_runs` como dicionários simples.
def list_recent_runs(limit: int = 50) -> list[dict]:
    factory = get_session_factory()
    session = factory()
    try:
        stmt = select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(limit)
        rows = session.scalars(stmt).all()
        return [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "vaga": r.vaga,
                "candidato": r.candidato,
                "final_score": r.final_score,
                "final_indication": r.final_indication,
                "pdf_path": r.pdf_path,
            }
            for r in rows
        ]
    finally:
        session.close()
