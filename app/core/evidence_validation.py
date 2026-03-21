"""Regra critica: nenhuma avaliacao sem evidencia com justificativa ancorada (minimo de caracteres)."""

from __future__ import annotations

from app.core.config import settings
from app.core.exceptions import EvidenceValidationError
from app.models.scorecard_models import Evidence


# Valida um bloco de evidencia pos-LLM ou proveniente de API.
def validate_evidence(ev: Evidence, *, min_justification_chars: int | None = None) -> None:
    m = min_justification_chars if min_justification_chars is not None else settings.MIN_EVIDENCE_JUSTIFICATION_CHARS
    j = (ev.justification or "").strip()
    if len(j) < m:
        raise EvidenceValidationError(
            f"Evaluation must include evidence-based justification (min {m} chars); got {len(j)}."
        )
    if not (ev.candidateAnswer or "").strip():
        raise EvidenceValidationError("Evidence must include the candidate answer text.")
    if not ev.questionId.strip():
        raise EvidenceValidationError("Evidence must include questionId.")


# Valida lista de evidencias para scorecard agregado.
def validate_evidence_list(evidence: list[Evidence], *, min_items: int = 1) -> None:
    if len(evidence) < min_items:
        raise EvidenceValidationError(
            f"At least {min_items} evidence item(s) required; got {len(evidence)}."
        )
    for ev in evidence:
        validate_evidence(ev)
