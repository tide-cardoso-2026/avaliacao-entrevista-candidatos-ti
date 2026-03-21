"""Carrega o banco de perguntas (JSON) para o question engine."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import BASE_DIR
from app.models.scorecard_models import Question

log = logging.getLogger(__name__)

DEFAULT_QUESTION_BANK_PATH = BASE_DIR / "data" / "question_bank" / "sample_questions.json"


# Lista perguntas a partir do arquivo JSON (valida com Pydantic).
def load_questions(path: Path | None = None) -> list[Question]:
    p = path or DEFAULT_QUESTION_BANK_PATH

    if not p.is_file():
        return []

    raw = json.loads(p.read_text(encoding="utf-8"))
    items = raw.get("questions", [])
    out: list[Question] = []
    for it in items:
        try:
            out.append(Question.model_validate(it))
        except Exception as exc:
            log.warning("Skip invalid question: %s", exc)
    return out


# Retorna perguntas situacionais obrigatorias (flag situational=true).
def load_situational_questions(path: Path | None = None) -> list[Question]:
    return [q for q in load_questions(path) if q.situational]
