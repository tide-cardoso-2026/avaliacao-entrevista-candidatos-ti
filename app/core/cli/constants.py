"""Extensões e pastas padrão da CLI."""

from __future__ import annotations

# Formatos aceitos para vaga, CV, entrevista e cliente.
VALID_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md", ".pdf", ".docx"})

# Subpastas de `data/` usadas pelo pipeline.
SUBDIR_JOB = "job_description"
SUBDIR_CANDIDATES = "candidates"
SUBDIR_CLIENTS = "clients"
SUBDIR_INTERVIEWS = "interviews"
