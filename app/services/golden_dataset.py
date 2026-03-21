"""Dataset dourado para calibracao: nota esperada por questionId."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

log = logging.getLogger(__name__)


class GoldenAnswer(BaseModel):

    model_config = ConfigDict(extra="forbid")

    questionId: str
    expectedScore: float = Field(ge=1.0, le=5.0)
    explanation: str = ""


# Carrega mapa questionId -> GoldenAnswer.
def load_golden_map(path: Path | None = None) -> dict[str, GoldenAnswer]:
    p = path or settings.GOLDEN_DATASET_PATH
    if not p.is_file():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    items = raw.get("goldenAnswers", [])
    out: dict[str, GoldenAnswer] = {}
    for it in items:
        try:
            g = GoldenAnswer.model_validate(it)
            out[g.questionId] = g
        except Exception as exc:
            log.warning("Skip invalid golden row: %s", exc)
    return out


def get_golden_for_question(question_id: str) -> GoldenAnswer | None:
    return load_golden_map().get(question_id)


def golden_self_check(*, ai_score: float, question_id: str) -> tuple[str | None, GoldenAnswer | None]:
    """Retorna (LOW_CONFIDENCE ou None, registro golden se existir)."""
    g = get_golden_for_question(question_id)
    if not g:
        return None, None
    if abs(ai_score - g.expectedScore) > 1.0:
        return "LOW_CONFIDENCE", g
    return None, g
