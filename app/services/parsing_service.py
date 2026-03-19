from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader
from docx import Document

from app.core.exceptions import DocumentNotFoundError, UnsupportedFormatError

log = logging.getLogger(__name__)


class ParsingService:
    """Extracts plain text from supported document formats."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}

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
    def _parse_pdf(path: Path) -> str:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts).strip()

    @staticmethod
    def _parse_docx(path: Path) -> str:
        doc = Document(str(path))
        parts: list[str] = []
        for para in doc.paragraphs:
            text = para.text or ""
            if text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts).strip()
