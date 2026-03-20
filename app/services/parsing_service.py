"""Leitura de arquivos locais (.txt, .md, .pdf, .docx) para texto plano usado no pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.core.exceptions import DocumentNotFoundError, UnsupportedFormatError

log = logging.getLogger(__name__)


# Extrai texto plano de formatos suportados para vaga, CV e transcrições.
class ParsingService:

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}

    # Lê o arquivo e retorna string; levanta se não existir ou formato inválido.
    def load_text(self, path: str | Path) -> str:
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise DocumentNotFoundError(f"Arquivo nao encontrado: {p}")

        suffix = p.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(f"Formato nao suportado para parsing: {suffix}")

        log.debug("Parsing %s (%s)", p.name, suffix)

        if suffix in {".txt", ".md"}:
            return p.read_text(encoding="utf-8", errors="ignore").strip()

        if suffix == ".pdf":
            return self._parse_pdf(p)

        return self._parse_docx(p)

    @staticmethod
    # Concatena texto extraído página a página via pypdf.
    def _parse_pdf(path: Path) -> str:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts).strip()

    @staticmethod
    # Junta parágrafos de um .docx em um único texto.
    def _parse_docx(path: Path) -> str:
        doc = Document(str(path))
        parts: list[str] = []
        for para in doc.paragraphs:
            text = para.text or ""
            if text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts).strip()
