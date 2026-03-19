from __future__ import annotations

from pathlib import Path
from typing import Iterable


class FileLocator:
    def __init__(self, *, root_data_dir: str | Path = "data") -> None:
        self.root_data_dir = Path(root_data_dir)

    def find_by_stem(self, *, subdir: str, stem_fragment: str, extensions: Iterable[str]) -> Path:
        base = self.root_data_dir / subdir
        if not base.exists():
            raise FileNotFoundError(f"Pasta de dados nao encontrada: {base}")

        ext_list = [e.lower().lstrip(".") for e in extensions]
        fragment = stem_fragment.lower().strip()
        if not fragment:
            raise ValueError("stem_fragment vazio")

        candidates: list[Path] = []
        for p in base.iterdir():
            if not p.is_file():
                continue
            if p.suffix.lower().lstrip(".") not in ext_list:
                continue
            if fragment in p.stem.lower():
                candidates.append(p)

        if len(candidates) == 0:
            raise FileNotFoundError(
                f"Nenhum arquivo encontrado em {base} com stem contendo '{stem_fragment}'. "
                f"Dica: use um nome como '*{stem_fragment}*.txt|md|pdf'."
            )
        if len(candidates) > 1:
            matches = "\n".join(f"- {c.name}" for c in sorted(candidates, key=lambda x: x.name))
            raise ValueError(
                f"Ambiguidade: mais de um arquivo encontrado em {base} para stem '{stem_fragment}'. "
                f"Refine o nome ou ajuste o stem.\n{matches}"
            )

        return candidates[0]

