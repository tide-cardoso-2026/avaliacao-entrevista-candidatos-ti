"""PDF com avaliacoes dos especialistas (lista + metricas de consolidacao opcionais)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.core.orchestration.middle_and_c_level import compute_weighted_score, detect_divergences
from app.core.pipeline_contract import compute_weighted_score_with_agent_weights
from app.models.schemas import AgentEvaluation


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
        .replace('"', "&quot;")
    )


def _bullets(styles: object, items: Iterable[str]) -> list[object]:
    out: list[object] = []
    for it in items:
        if not it:
            continue
        out.append(Paragraph(f"• {_esc(it)}", styles["BodyText"]))
    if not out:
        out.append(Paragraph("• (nenhum item)", styles["BodyText"]))
    return out


def _safe_fragment(text: str, max_len: int = 40) -> str:
    s = "".join(c if c.isalnum() or c in " -_" else "_" for c in text)[:max_len].strip()
    return "_".join(s.split()) or "doc"


# Grava PDF com avaliacoes dos assistentes. Opcionalmente inclui bloco de consolidacao (pre-middle).
def write_assistants_evaluation_pdf(
    *,
    output_dir: Path,
    evaluations: list[AgentEvaluation],
    job_title: str,
    candidate_name: str,
    title: str,
    footer_note: str,
    filename_stem: str | None = None,
    prompt_excerpt: str | None = None,
    include_consolidation_summary: bool = False,
    evaluations_section_title: str = "Avaliacoes por especialista",
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_cand = _safe_fragment(candidate_name)
    safe_job = _safe_fragment(job_title)
    if filename_stem:
        stem = filename_stem
    else:
        stem = f"assistants_pre_middle_{safe_cand}_{safe_job}_{ts}"
    out_path = output_dir / f"{stem}.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out_path), pagesize=A4, title=title.split("\n")[0][:120])

    story: list[object] = []
    story.append(Paragraph(_esc(title), styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Vaga:</b> {_esc(job_title)}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Candidato:</b> {_esc(candidate_name)}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Gerado em:</b> {_esc(ts)}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    if include_consolidation_summary and evaluations:
        w_conf = compute_weighted_score(evaluations)
        w_agent = compute_weighted_score_with_agent_weights(evaluations)
        story.append(Paragraph("Consolidacao (metricas objetivas)", styles["Heading2"]))
        story.append(
            Paragraph(
                f"Media ponderada por confianca: <b>{w_conf:.2f}</b>/10<br/>"
                f"Media ponderada por perfil de agente: <b>{w_agent:.2f}</b>/10",
                styles["BodyText"],
            )
        )
        divs = detect_divergences(evaluations)
        if divs:
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Divergencias detectadas</b>", styles["BodyText"]))
            for d in divs:
                story.append(Paragraph(f"• {_esc(d.description)}", styles["BodyText"]))
        story.append(Spacer(1, 12))

    story.append(Paragraph(_esc(evaluations_section_title), styles["Heading2"]))
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
            if ev.structured_risks:
                story.append(Spacer(1, 4))
                story.append(Paragraph("<b>Riscos estruturados</b>", styles["BodyText"]))
                for r in ev.structured_risks:
                    story.append(
                        Paragraph(
                            f"• [{_esc(r.severity)}] {_esc(r.description)}",
                            styles["BodyText"],
                        )
                    )
            if ev.missing_evidence:
                story.append(Spacer(1, 4))
                story.append(Paragraph("<b>Evidencias ausentes</b>", styles["BodyText"]))
                story.extend(_bullets(styles, ev.missing_evidence))
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
