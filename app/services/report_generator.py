from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.schemas import (
    AgentEvaluation,
    CTOFinalEvaluation,
    FinalIndication,
    FinalRating,
    MiddleManagementEvaluation,
)


class ReportGenerator:
    def __init__(self, *, output_dir: str | Path = "outputs/reports") -> None:
        self.output_dir = Path(output_dir)

    def generate_report(
        self,
        *,
        vaga: str,
        candidato: str,
        assistant_evaluations: list[AgentEvaluation],
        middle_management_evaluation: MiddleManagementEvaluation,
        cto_evaluation: CTOFinalEvaluation,
    ) -> str:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%y%m%d_%H%M")
        out_path = self.output_dir / f"{candidato}_{vaga}_{ts}.pdf"

        styles = self._build_styles()
        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=A4,
            title="Laudo Tecnico",
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        story: list[object] = []
        story.append(Paragraph("Laudo Tecnico de Avaliacao", styles["ReportTitle"]))
        story.append(Paragraph("Sistema de Avaliacao Inteligente de Candidatos", styles["Subtitle"]))
        story.append(Spacer(1, 10))

        story.append(
            self._meta_table(
                vaga=vaga,
                candidato=candidato,
                generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
                styles=styles,
            )
        )
        story.append(Spacer(1, 14))

        story.append(Paragraph("Resumo Executivo", styles["SectionTitle"]))
        story.append(
            self._kpi_table(
                rows=[
                    ("Rating Final", cto_evaluation.final_rating.value),
                    ("Indicacao", cto_evaluation.final_indication.value),
                    ("Score Final", f"{cto_evaluation.score_final:.2f}/10"),
                    ("Confianca", f"{cto_evaluation.confidence * 100:.0f}%"),
                ],
                styles=styles,
            )
        )
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#D3DCE6")))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Avaliacoes por Assistente", styles["SectionTitle"]))
        if not assistant_evaluations:
            story.append(Paragraph("Nenhuma avaliacao disponivel no MVP atual.", styles["BodyText"]))
        else:
            for idx, ev in enumerate(assistant_evaluations, start=1):
                story.extend(self._assistant_block(index=idx, evaluation=ev, styles=styles))
                story.append(Spacer(1, 8))

        story.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#D3DCE6")))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Consolidacao Middle Management", styles["SectionTitle"]))
        mm = middle_management_evaluation
        story.append(self._simple_highlight(f"Score Consolidado: <b>{mm.score_consolidated:.2f}/10</b>", styles))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Conflitos", styles["SubsectionTitle"]))
        story.extend(self._bullet_paragraphs(mm.conflicts, styles["BulletText"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Questoes Criticas", styles["SubsectionTitle"]))
        story.extend(self._bullet_paragraphs(mm.critical_questions, styles["BulletText"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Analise", styles["SubsectionTitle"]))
        story.append(Paragraph(self._esc(mm.analysis), styles["BodyText"]))
        story.append(Spacer(1, 10))

        story.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#D3DCE6")))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Analise C-Level (CTO)", styles["SectionTitle"]))
        story.append(
            self._kpi_table(
                rows=[
                    ("Rating", cto_evaluation.final_rating.value),
                    ("Indicacao", cto_evaluation.final_indication.value),
                    ("Score Final", f"{cto_evaluation.score_final:.2f}/10"),
                    ("Confianca", f"{cto_evaluation.confidence * 100:.0f}%"),
                ],
                styles=styles,
            )
        )
        story.append(Spacer(1, 6))
        story.append(Paragraph("Riscos", styles["SubsectionTitle"]))
        story.extend(self._bullet_paragraphs(cto_evaluation.risks, styles["BulletText"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Observacoes", styles["SubsectionTitle"]))
        story.append(Paragraph(self._esc(cto_evaluation.observations), styles["BodyText"]))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Riscos (Resumo Consolidado)", styles["SectionTitle"]))
        all_risks = list(dict.fromkeys([*mm.conflicts, *cto_evaluation.risks]))
        story.extend(
            self._bullet_paragraphs(
                all_risks if all_risks else ["(Nenhum risco informado)"], styles["BulletText"]
            )
        )
        story.append(Spacer(1, 10))

        story.append(Paragraph("Conclusao e Recomendacao Final", styles["SectionTitle"]))
        story.append(
            self._simple_highlight(
                f"Recomendacao: <b>{self._esc(cto_evaluation.final_indication.value)}</b>",
                styles,
            )
        )
        story.append(Spacer(1, 6))
        story.append(Paragraph("Observacoes", styles["SubsectionTitle"]))
        story.append(Paragraph(self._esc(cto_evaluation.observations), styles["BodyText"]))

        doc.build(story)
        return str(out_path)

    def generate_minimal_report(self, *, vaga: str, candidato: str) -> str:
        # Utilizado pelo smoke test do scaffold.
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
        # Nao ha avaliacoes no smoke test.
        return self.generate_report(
            vaga=vaga,
            candidato=candidato,
            assistant_evaluations=[],
            middle_management_evaluation=mm,
            cto_evaluation=cto,
        )

    def generate_ranking_report(
        self,
        *,
        vaga: str,
        rankings: list[tuple[str, CTOFinalEvaluation]],
    ) -> str:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%y%m%d_%H%M")
        out_path = self.output_dir / f"comparativo_{vaga}_{ts}.pdf"

        styles = self._build_styles()
        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=A4,
            title="Ranking de Candidatos",
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        story: list[object] = []

        story.append(Paragraph("Ranking Consolidado de Candidatos", styles["ReportTitle"]))
        story.append(Paragraph("Comparativo para tomada de decisao", styles["Subtitle"]))
        story.append(Spacer(1, 10))
        story.append(
            self._meta_table(
                vaga=vaga,
                candidato="Multiplo",
                generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
                styles=styles,
            )
        )
        story.append(Spacer(1, 10))

        if not rankings:
            story.append(Paragraph("Nenhum candidato avaliado.", styles["BodyText"]))
        else:
            ordered = sorted(rankings, key=lambda x: float(x[1].score_final), reverse=True)
            story.append(Paragraph("Ranking Final", styles["SectionTitle"]))
            story.append(Spacer(1, 6))
            table_rows = [
                [
                    Paragraph("<b>Posicao</b>", styles["TableHeader"]),
                    Paragraph("<b>Candidato</b>", styles["TableHeader"]),
                    Paragraph("<b>Score</b>", styles["TableHeader"]),
                    Paragraph("<b>Rating</b>", styles["TableHeader"]),
                    Paragraph("<b>Indicacao</b>", styles["TableHeader"]),
                ]
            ]
            for idx, (candidato, cto) in enumerate(ordered, start=1):
                table_rows.append(
                    [
                        Paragraph(str(idx), styles["TableCell"]),
                        Paragraph(self._esc(candidato), styles["TableCell"]),
                        Paragraph(f"{cto.score_final:.2f}", styles["TableCell"]),
                        Paragraph(self._esc(cto.final_rating.value), styles["TableCell"]),
                        Paragraph(self._esc(cto.final_indication.value), styles["TableCell"]),
                    ]
                )
            ranking_table = Table(table_rows, colWidths=[48, 170, 70, 100, 130], repeatRows=1)
            ranking_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (0, 0), (0, -1), "CENTER"),
                        ("ALIGN", (2, 1), (2, -1), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C6D2E1")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(ranking_table)

        doc.build(story)
        return str(out_path)

    def _assistant_block(
        self, *, index: int, evaluation: AgentEvaluation, styles: StyleSheet1
    ) -> list[object]:
        header = Table(
            [
                [
                    Paragraph(f"{index:02d}", styles["AgentIndex"]),
                    Paragraph(self._esc(evaluation.agent_name), styles["AgentHeaderText"]),
                ],
                [
                    Paragraph("", styles["AgentIndex"]),
                    Paragraph(
                        (
                            f"<b>Dominio:</b> {self._esc(evaluation.domain)} | "
                            f"<b>Score:</b> {evaluation.score:.2f}/10 | "
                            f"<b>Confianca:</b> {evaluation.confidence * 100:.0f}% | "
                            f"<b>Score Ponderado:</b> {evaluation.weighted_score:.2f}"
                        ),
                        styles["AgentMeta"],
                    ),
                ],
            ],
            colWidths=[38, 490],
        )
        header.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (0, 1)),
                    ("BACKGROUND", (0, 0), (0, 1), colors.HexColor("#1E3A5F")),
                    ("BACKGROUND", (1, 0), (1, 1), colors.HexColor("#EEF3F8")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B7C5D6")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#B7C5D6")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        block: list[object] = [header, Spacer(1, 6)]
        block.append(Paragraph("Pontos Fortes", styles["SubsectionTitle"]))
        block.extend(self._bullet_paragraphs(evaluation.strengths, styles["BulletText"]))
        block.append(Spacer(1, 3))
        block.append(Paragraph("Pontos de Melhoria", styles["SubsectionTitle"]))
        block.extend(self._bullet_paragraphs(evaluation.improvements, styles["BulletText"]))
        block.append(Spacer(1, 3))
        block.append(Paragraph("Riscos", styles["SubsectionTitle"]))
        block.extend(self._bullet_paragraphs(evaluation.risks, styles["BulletText"]))
        block.append(Spacer(1, 3))
        block.append(Paragraph("Recomendacao", styles["SubsectionTitle"]))
        block.append(Paragraph(self._esc(evaluation.recommendation), styles["BodyText"]))

        return [KeepTogether(block)]

    def _meta_table(
        self, *, vaga: str, candidato: str, generated_at: str, styles: StyleSheet1
    ) -> Table:
        table = Table(
            [
                [
                    Paragraph("<b>Vaga</b>", styles["MetaLabel"]),
                    Paragraph(self._esc(vaga), styles["MetaValue"]),
                    Paragraph("<b>Candidato</b>", styles["MetaLabel"]),
                    Paragraph(self._esc(candidato), styles["MetaValue"]),
                ],
                [
                    Paragraph("<b>Gerado em</b>", styles["MetaLabel"]),
                    Paragraph(self._esc(generated_at), styles["MetaValue"]),
                    Paragraph("<b>Fonte</b>", styles["MetaLabel"]),
                    Paragraph("Pipeline Multiagente", styles["MetaValue"]),
                ],
            ],
            colWidths=[70, 170, 80, 196],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C6D2E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6E0EA")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _kpi_table(self, *, rows: list[tuple[str, str]], styles: StyleSheet1) -> Table:
        headers = [Paragraph(f"<b>{self._esc(label)}</b>", styles["KpiHeader"]) for label, _ in rows]
        values = [Paragraph(self._esc(value), styles["KpiValue"]) for _, value in rows]
        table = Table([headers, values], colWidths=[129, 129, 129, 129])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#EEF3F8")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B7C5D6")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#B7C5D6")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _simple_highlight(self, text: str, styles: StyleSheet1) -> Table:
        table = Table([[Paragraph(text, styles["BodyText"])]], colWidths=[516])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF3F8")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B7C5D6")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    def _bullet_paragraphs(self, items: Iterable[str], style: ParagraphStyle) -> list[Paragraph]:
        result: list[Paragraph] = []
        for it in items:
            if not it:
                continue
            result.append(Paragraph(f"• {self._esc(it)}", style))
        if not result:
            # Evita seccoes vazias quebrando layout.
            result.append(Paragraph("• (Nenhum item informado)", style))
        return result

    def _build_styles(self) -> StyleSheet1:
        styles = getSampleStyleSheet()
        styles["Title"].fontName = "Helvetica-Bold"
        styles["BodyText"].fontName = "Helvetica"
        styles["BodyText"].fontSize = 10
        styles["BodyText"].leading = 14
        styles["BodyText"].textColor = colors.HexColor("#1E293B")

        styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=styles["Title"],
                fontSize=22,
                leading=26,
                textColor=colors.HexColor("#1E3A5F"),
                spaceAfter=2,
            )
        )
        styles.add(
            ParagraphStyle(
                name="Subtitle",
                parent=styles["BodyText"],
                fontSize=10,
                leading=12,
                textColor=colors.HexColor("#4A6078"),
                spaceAfter=8,
            )
        )
        styles.add(
            ParagraphStyle(
                name="SectionTitle",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=16,
                textColor=colors.HexColor("#1E3A5F"),
                spaceBefore=3,
                spaceAfter=5,
            )
        )
        styles.add(
            ParagraphStyle(
                name="SubsectionTitle",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#1E3A5F"),
                spaceBefore=2,
                spaceAfter=2,
            )
        )
        styles.add(
            ParagraphStyle(
                name="BulletText",
                parent=styles["BodyText"],
                leftIndent=8,
                spaceAfter=1,
            )
        )
        styles.add(ParagraphStyle(name="MetaLabel", parent=styles["BodyText"], textColor=colors.HexColor("#3A4A5E")))
        styles.add(ParagraphStyle(name="MetaValue", parent=styles["BodyText"]))
        styles.add(
            ParagraphStyle(
                name="KpiHeader",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=9,
                leading=11,
            )
        )
        styles.add(
            ParagraphStyle(
                name="KpiValue",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=13,
            )
        )
        styles.add(
            ParagraphStyle(
                name="AgentIndex",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=11,
                textColor=colors.white,
                alignment=1,
            )
        )
        styles.add(
            ParagraphStyle(
                name="AgentHeaderText",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=11,
                textColor=colors.HexColor("#1E3A5F"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="AgentMeta",
                parent=styles["BodyText"],
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#334155"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="TableHeader",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                textColor=colors.white,
                fontSize=9,
                leading=11,
            )
        )
        styles.add(
            ParagraphStyle(
                name="TableCell",
                parent=styles["BodyText"],
                fontSize=9,
                leading=12,
            )
        )
        return styles

    @staticmethod
    def _esc(text: str) -> str:
        # ReportLab Paragraph usa um subconjunto de HTML-like tags.
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
            .replace('"', "&quot;")
        )

