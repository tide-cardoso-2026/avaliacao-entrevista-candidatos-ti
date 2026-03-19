from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

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

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(out_path), pagesize=A4, title="Laudo Tecnico")

        story: list[object] = []
        story.append(Paragraph("Sistema de Avaliacao Inteligente - Laudo Tecnico", styles["Title"]))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Resumo Executivo", styles["Heading2"]))
        story.append(
            Paragraph(
                f"Rating Final: <b>{cto_evaluation.final_rating.value}</b> | "
                f"Indicacao: <b>{cto_evaluation.final_indication.value}</b> | "
                f"Score Final: <b>{cto_evaluation.score_final:.2f}</b>",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 10))

        story.append(Paragraph("Avaliacoes por Assistente", styles["Heading2"]))
        if not assistant_evaluations:
            story.append(Paragraph("Nenhuma avaliacao disponivel no MVP atual.", styles["BodyText"]))
        else:
            for ev in assistant_evaluations:
                story.append(Paragraph(f"{ev.agent_name} - Score {ev.score:.2f}/10", styles["Heading3"]))
                story.append(Paragraph(f"<b>Dominio:</b> {ev.domain}", styles["BodyText"]))
                story.append(Spacer(1, 6))
                story.append(Paragraph("<b>Pontos Fortes</b>", styles["BodyText"]))
                story.extend(self._bullet_paragraphs(ev.strengths))
                story.append(Spacer(1, 4))
                story.append(Paragraph("<b>Pontos de Melhoria</b>", styles["BodyText"]))
                story.extend(self._bullet_paragraphs(ev.improvements))
                story.append(Spacer(1, 4))
                story.append(Paragraph("<b>Riscos</b>", styles["BodyText"]))
                story.extend(self._bullet_paragraphs(ev.risks))
                story.append(Spacer(1, 4))
                story.append(Paragraph("<b>Recomendacao</b>", styles["BodyText"]))
                story.append(Paragraph(self._esc(ev.recommendation), styles["BodyText"]))
                story.append(Spacer(1, 10))

        story.append(Paragraph("Consolidacao Middle Management", styles["Heading2"]))
        mm = middle_management_evaluation
        story.append(
            Paragraph(f"Score Consolidado: <b>{mm.score_consolidated:.2f}</b>", styles["BodyText"])
        )
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Conflitos</b>", styles["BodyText"]))
        story.extend(self._bullet_paragraphs(mm.conflicts))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Questoes Criticas</b>", styles["BodyText"]))
        story.extend(self._bullet_paragraphs(mm.critical_questions))
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Analise</b>", styles["BodyText"]))
        story.append(Paragraph(self._esc(mm.analysis), styles["BodyText"]))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Analise C-Level (CTO)", styles["Heading2"]))
        story.append(
            Paragraph(
                f"Rating: <b>{cto_evaluation.final_rating.value}</b> | "
                f"Indicacao: <b>{cto_evaluation.final_indication.value}</b> | "
                f"Score Final: <b>{cto_evaluation.score_final:.2f}</b>",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Riscos</b>", styles["BodyText"]))
        story.extend(self._bullet_paragraphs(cto_evaluation.risks))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Observacoes</b>", styles["BodyText"]))
        story.append(Paragraph(self._esc(cto_evaluation.observations), styles["BodyText"]))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Score Final e Recomendacao Final", styles["Heading2"]))
        story.append(
            Paragraph(
                f"Score Final: <b>{cto_evaluation.score_final:.2f}</b><br/>"
                f"Recomendacao: <b>{cto_evaluation.final_indication.value}</b>",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 10))

        story.append(Paragraph("Riscos (Resumo)", styles["Heading2"]))
        all_risks = list(dict.fromkeys([*mm.conflicts, *cto_evaluation.risks]))
        story.extend(self._bullet_paragraphs(all_risks if all_risks else ["- (Nenhum risco informado)"]))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Observacoes", styles["Heading2"]))
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

    def _bullet_paragraphs(self, items: Iterable[str]) -> list[Paragraph]:
        result: list[Paragraph] = []
        for it in items:
            if not it:
                continue
            result.append(Paragraph(f"• {self._esc(it)}", getSampleStyleSheet()["BodyText"]))
        if not result:
            # Evita seccoes vazias quebrando layout.
            result.append(Paragraph("• (Nenhum item informado)", getSampleStyleSheet()["BodyText"]))
        return result

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

