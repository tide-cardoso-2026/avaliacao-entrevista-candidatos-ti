"""Geração de PDF (ReportLab): laudo executivo consolidado e ranking comparativo."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.executive_report import ExecutiveEvaluationReport
from app.models.schemas import CTOFinalEvaluation
from app.services.executive_report_service import (
    WEIGHT_ARCHITECTURE,
    WEIGHT_COMMUNICATION,
    WEIGHT_PRODUCT,
    WEIGHT_TECHNICAL,
    build_fallback_executive_report,
    normalize_executive_report,
    weighted_final_score as exec_weighted_final_score,
)


# Rótulos PT-BR para recomendação e nível.
def _label_recommendation(code: str) -> str:
    if code == "STRONG_HIRE":
        return "Contratar (forte)"
    if code == "NO_HIRE":
        return "Não contratar"
    return "Aprovar"


def _label_level(code: str) -> str:
    return {
        "junior": "Júnior",
        "mid": "Pleno",
        "senior": "Senior",
        "staff": "Staff",
    }.get(code.lower(), code)


# Monta PDF executivo a partir do contrato `ExecutiveEvaluationReport`.
class ReportGenerator:
    # Define diretório de saída dos relatórios (criado sob demanda).
    def __init__(self, *, output_dir: str | Path = "outputs/reports") -> None:
        self.output_dir = Path(output_dir)

    # PDF executivo (1–2 páginas): capa, scorecard, consolidação, domínios, fit.
    def generate_report(
        self,
        *,
        vaga: str,
        candidato: str,
        executive: ExecutiveEvaluationReport,
    ) -> str:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%y%m%d_%H%M")
        out_path = self.output_dir / f"{candidato}_{vaga}_{ts}.pdf"

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(out_path), pagesize=A4, title="Laudo Executivo")
        story: list[object] = []

        story.append(Paragraph("Avaliacao de Candidato", styles["Title"]))
        story.append(Spacer(1, 8))
        story.append(
            Paragraph(
                f"<b>Candidato:</b> {self._esc(executive.candidate.name)}<br/>"
                f"<b>Vaga:</b> {self._esc(executive.candidate.role)}<br/>"
                f"<b>Data:</b> {self._esc(executive.candidate.date)}",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 10))

        d = executive.decision
        story.append(Paragraph("Decisao Final", styles["Heading2"]))
        conf_pct = int(round(d.confidence * 100))
        story.append(
            Paragraph(
                f"<b>Recomendacao:</b> {_label_recommendation(d.recommendation)}<br/>"
                f"<b>Nivel:</b> {_label_level(d.level)}<br/>"
                f"<b>Score:</b> {d.score:.1f} / 10<br/>"
                f"<b>Confianca:</b> {conf_pct}%",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 10))

        h = executive.highlights
        story.append(Paragraph("Principais Riscos", styles["Heading2"]))
        story.extend(self._bullet_paragraphs(h.risks or ["(Nenhum risco informado)"]))
        story.append(Spacer(1, 8))
        story.append(Paragraph("Principais Forcas", styles["Heading2"]))
        story.extend(self._bullet_paragraphs(h.strengths or ["(Nenhum item informado)"]))
        story.append(Spacer(1, 8))
        story.append(Paragraph("Principais Gaps", styles["Heading2"]))
        story.extend(self._bullet_paragraphs(h.gaps or ["(Nenhum gap informado)"]))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Leitura Executiva (Resumo)", styles["Heading2"]))
        story.append(Paragraph(self._esc(executive.summary), styles["BodyText"]))
        story.append(Spacer(1, 8))

        sb = executive.score_breakdown
        wf = exec_weighted_final_score(sb)
        data = [
            ["Dimensao", "Score", "Peso", "Resultado"],
            [
                "Tecnico",
                f"{sb.technical:.1f}",
                "40%",
                f"{sb.technical * WEIGHT_TECHNICAL:.2f}",
            ],
            [
                "Arquitetura",
                f"{sb.architecture:.1f}",
                "30%",
                f"{sb.architecture * WEIGHT_ARCHITECTURE:.2f}",
            ],
            [
                "Produto",
                f"{sb.product:.1f}",
                "20%",
                f"{sb.product * WEIGHT_PRODUCT:.2f}",
            ],
            [
                "Comunicacao",
                f"{sb.communication:.1f}",
                "10%",
                f"{sb.communication * WEIGHT_COMMUNICATION:.2f}",
            ],
            ["", "", "Score final:", f"{wf:.1f}"],
        ]
        tbl = Table(data, colWidths=[1.8 * cm, 1.6 * cm, 1.6 * cm, 1.8 * cm])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ]
            )
        )
        story.append(Paragraph("Score por Dimensao", styles["Heading2"]))
        story.append(Spacer(1, 6))
        story.append(tbl)
        story.append(Spacer(1, 10))

        ca = executive.consolidated_analysis
        story.append(Paragraph("Analise Consolidada", styles["Heading2"]))
        story.append(Paragraph(self._esc("Pontos Fortes"), styles["Heading3"]))
        story.extend(self._bullet_paragraphs(ca.strengths))
        story.append(Paragraph(self._esc("Pontos de Atencao"), styles["Heading3"]))
        story.extend(self._bullet_paragraphs(ca.attention_points))
        story.append(Paragraph(self._esc("Riscos"), styles["Heading3"]))
        story.extend(self._bullet_paragraphs(ca.risks))
        story.append(Spacer(1, 8))

        dom = executive.domain_analysis
        story.append(Paragraph("Avaliacao por Dominio (resumida)", styles["Heading2"]))
        self._domain_section(story, styles, "Backend", dom.backend)
        self._domain_section(story, styles, "Frontend", dom.frontend)
        self._domain_section(story, styles, "DevOps", dom.devops)
        self._domain_section(story, styles, "Seguranca", dom.security)
        self._domain_section(story, styles, "Comportamental", dom.behavioral)
        story.append(Spacer(1, 8))

        if executive.conflicts:
            story.append(Paragraph("Conflitos de Avaliacao", styles["Heading2"]))
            story.extend(self._bullet_paragraphs(executive.conflicts))
            story.append(Spacer(1, 8))

        fit = executive.fit
        story.append(Paragraph("Fit para a Vaga", styles["Heading2"]))
        story.append(
            Paragraph(
                f"<b>Senioridade esperada:</b> {self._esc(fit.expected_level)}<br/>"
                f"<b>Senioridade avaliada:</b> {self._esc(fit.evaluated_level)}<br/>"
                f"<b>Gap (niveis):</b> {fit.gap}<br/>"
                f"<b>Recomendacao:</b> {self._esc(fit.recommendation)}",
                styles["BodyText"],
            )
        )

        doc.build(story)
        return str(out_path)

    # Laudo com placeholders (smoke test); usa fallback determinístico.
    def generate_minimal_report(self, *, vaga: str, candidato: str) -> str:
        from app.models.schemas import FinalIndication, FinalRating, MiddleManagementEvaluation

        mm = MiddleManagementEvaluation(
            score_consolidated=0.0,
            conflicts=[],
            critical_questions=[],
            analysis="(MVP) Analise ainda nao executada.",
        )
        cto = CTOFinalEvaluation(
            final_rating=FinalRating.Estagiario,
            score_final=0.0,
            final_indication=FinalIndication.AprovarComRessalvas,
            risks=[],
            observations="(MVP) Analise ainda nao executada.",
        )
        ex = normalize_executive_report(
            build_fallback_executive_report(
                vaga=vaga,
                candidato_display=candidato,
                assistant_evaluations=[],
                middle=mm,
                cto=cto,
            )
        )
        return self.generate_report(vaga=vaga, candidato=candidato, executive=ex)

    # PDF comparativo ordenando candidatos pelo score final do CTO.
    def generate_ranking_report(
        self,
        *,
        vaga: str,
        rankings: list[tuple[str, CTOFinalEvaluation]],
    ) -> str:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%y%m%d_%H%M")
        out_path = self.output_dir / f"comparativo_{vaga}_{ts}.pdf"

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(out_path), pagesize=A4, title="Ranking de Candidatos")
        story: list[object] = []

        story.append(Paragraph("Ranking Consolidado de Candidatos", styles["Title"]))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Vaga: <b>{self._esc(vaga)}</b>", styles["BodyText"]))
        story.append(Spacer(1, 10))

        if not rankings:
            story.append(Paragraph("Nenhum candidato avaliado.", styles["BodyText"]))
        else:
            ordered = sorted(rankings, key=lambda x: float(x[1].score_final), reverse=True)
            story.append(Paragraph("Ranking Final", styles["Heading2"]))
            story.append(Spacer(1, 6))
            for idx, (candidato, cto) in enumerate(ordered, start=1):
                story.append(
                    Paragraph(
                        f"{idx}. <b>{self._esc(candidato)}</b> | "
                        f"Score: <b>{cto.score_final:.2f}</b> | "
                        f"Rating: <b>{self._esc(cto.final_rating.value)}</b> | "
                        f"Indicacao: <b>{self._esc(cto.final_indication.value)}</b>",
                        styles["BodyText"],
                    )
                )
                story.append(Spacer(1, 4))

        doc.build(story)
        return str(out_path)

    # Secção opcional por domínio (omitir se vazia).
    def _domain_section(
        self,
        story: list[object],
        styles: object,
        title: str,
        items: Iterable[str],
    ) -> None:
        lst = [x for x in items if (x or "").strip()]
        if not lst:
            return
        story.append(Paragraph(self._esc(title), styles["Heading3"]))
        story.extend(self._bullet_paragraphs(lst))

    # Converte lista de strings em parágrafos com marcadores para o PDF.
    def _bullet_paragraphs(self, items: Iterable[str]) -> list[Paragraph]:
        styles = getSampleStyleSheet()
        result: list[Paragraph] = []
        for it in items:
            if not it:
                continue
            result.append(Paragraph(f"• {self._esc(it)}", styles["BodyText"]))
        if not result:
            result.append(Paragraph("• (Nenhum item informado)", styles["BodyText"]))
        return result

    @staticmethod
    # Escapa HTML/XML mínimo para `Paragraph` do ReportLab.
    def _esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
            .replace('"', "&quot;")
        )
