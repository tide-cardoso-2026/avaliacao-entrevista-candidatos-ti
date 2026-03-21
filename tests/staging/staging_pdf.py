"""PDF de saida para testes de staging (camada de assistentes)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.models.schemas import AgentEvaluation
from app.services.assistants_evaluation_pdf import write_assistants_evaluation_pdf


# Grava PDF com avaliacoes dos assistentes em `output_dir`.
# Retorna o caminho do arquivo criado.
def write_assistants_staging_pdf(
    *,
    output_dir: Path,
    evaluations: list[AgentEvaluation],
    job_title: str,
    candidate_name: str,
    prompt_excerpt: str | None = None,
    footer_note: str = "Gerado automaticamente pelo teste de staging (python -m pytest).",
) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_cand = "".join(c if c.isalnum() or c in " -_" else "_" for c in candidate_name)[:40].strip() or "candidato"
    safe_cand = "_".join(safe_cand.split())
    return write_assistants_evaluation_pdf(
        output_dir=output_dir,
        evaluations=evaluations,
        job_title=job_title,
        candidate_name=candidate_name,
        title="EntrevistaTaking — Relatorio de staging (assistentes)",
        footer_note=footer_note,
        filename_stem=f"staging_assistants_{safe_cand}_{ts}",
        prompt_excerpt=prompt_excerpt,
        include_consolidation_summary=False,
        evaluations_section_title="Avaliacoes dos assistentes",
    )
