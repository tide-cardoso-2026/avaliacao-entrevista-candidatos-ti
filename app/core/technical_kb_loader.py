"""Carrega trechos da base `data/technical-questions/*.md` para injeção no prompt dos assistentes."""

from __future__ import annotations

from pathlib import Path


# Lê o arquivo de KB; trunca se exceder `max_chars` (evita estourar contexto do modelo).
def read_technical_kb_file(
    *,
    base_dir: Path,
    filename: str | None,
    max_chars: int,
) -> str:
    if not filename or not str(filename).strip():
        return ""
    path = base_dir / filename.strip()
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n... [truncado por TECHNICAL_KB_MAX_CHARS]"
