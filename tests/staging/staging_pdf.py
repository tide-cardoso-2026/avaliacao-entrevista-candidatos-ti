"""PDF de saida para testes de staging (camada de assistentes)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.models.schemas import AgentEvaluation


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
        .replace('"', "&quot;")
    )


def _bullets(styles, items: Iterable[str]) -> list[object]:
    out: list[object] = []
    for it in items:
        if not it:
            continue
        out.append(Paragraph(f"• {_esc(it)}", styles["BodyText"]))
    if not out:
        out.append(Paragraph("• (nenhum item)", styles["BodyText"]))
    return out


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
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_cand = "".join(c if c.isalnum() or c in " -_" else "_" for c in candidate_name)[:40].strip() or "candidato"
    safe_cand = "_".join(safe_cand.split())
    out_path = output_dir / f"staging_assistants_{safe_cand}_{ts}.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out_path), pagesize=A4, title="Staging — Assistentes")

    story: list[object] = []
    story.append(Paragraph("EntrevistaTaking — Relatorio de staging (assistentes)", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Vaga:</b> {_esc(job_title)}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Candidato:</b> {_esc(candidate_name)}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Gerado em:</b> {_esc(ts)}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Avaliacoes dos assistentes", styles["Heading2"]))
    if not evaluations:
        story.append(Paragraph("Nenhuma avaliacao retornada.", styles["BodyText"]))
    else:
        for ev in evaluations:
            story.append(
                Paragraph(
                    f"{_esc(ev.agent_name)} — score {_esc(f'{ev.score:.2f}')}/10 "
                    f"(confianca {_esc(f'{ev.confidence:.2f}')}, ponderado {_esc(f'{ev.weighted_score:.2f}')})",
                    styles["Heading3"],
                )
            )
            story.append(Paragraph(f"<b>Dominio:</b> {_esc(ev.domain)}", styles["BodyText"]))
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Pontos fortes</b>", styles["BodyText"]))
            story.extend(_bullets(styles, ev.strengths))
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Pontos de melhoria</b>", styles["BodyText"]))
            story.extend(_bullets(styles, ev.improvements))
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Riscos</b>", styles["BodyText"]))
            story.extend(_bullets(styles, ev.risks))
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Recomendacao</b>", styles["BodyText"]))
            story.append(Paragraph(_esc(ev.recommendation), styles["BodyText"]))
            story.append(Spacer(1, 10))

    if prompt_excerpt:
        story.append(Paragraph("Trecho do prompt enviado ao assistente (auditoria)", styles["Heading2"]))
        excerpt = prompt_excerpt if len(prompt_excerpt) <= 8000 else prompt_excerpt[:8000] + "\n\n[... truncado ...]"
        story.append(Paragraph(_esc(excerpt), styles["BodyText"]))
        story.append(Spacer(1, 10))

    story.append(Paragraph("<i>" + _esc(footer_note) + "</i>", styles["BodyText"]))

    doc.build(story)
    return out_path
