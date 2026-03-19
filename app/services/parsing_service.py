from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


class ParsingService:
    """
    Carrega documentos e extrai texto para o pipeline.
    """

    def load_text(self, path: str | Path) -> str:
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Arquivo nao encontrado: {p}")

        suffix = p.suffix.lower()
        if suffix in {".txt", ".md"}:
            return p.read_text(encoding="utf-8", errors="ignore").strip()
        if suffix == ".pdf":
            reader = PdfReader(str(p))
            parts: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(text.strip())
            return "\n\n".join(parts).strip()

        raise ValueError(f"Formato nao suportado para parsing: {suffix}")

