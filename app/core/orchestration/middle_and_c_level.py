from __future__ import annotations

import json
from pathlib import Path

from app.models.schemas import (
    AgentEvaluation,
    CTOFinalEvaluation,
    FinalIndication,
    FinalRating,
    MiddleManagementEvaluation,
)


class MiddleManagementConsolidator:
    def __init__(self, *, llm_service: object, prompts_root: str | Path = "prompts") -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)
        # Se existirem templates especializados das issues (#2-#4), rodamos todos e consolidamos.
        self.prompt_paths: list[Path] = [
            self.prompts_root / "middle_management" / "tech_manager.md",
            self.prompts_root / "middle_management" / "product_manager.md",
            self.prompts_root / "middle_management" / "sre_manager.md",
        ]
        if not all(p.exists() for p in self.prompt_paths):
            self.prompt_paths = [self.prompts_root / "middle_management" / "generic_consolidator.md"]

    def run(self, *, assistant_evaluations: list[AgentEvaluation]) -> MiddleManagementEvaluation:
        # Mantem API compatível com o scaffold inicial.
        return self.run_with_documents(
            assistant_evaluations=assistant_evaluations,
            job_description_text="",
            cv_candidate_text="",
            cv_client_text="",
            interview_transcript_text="",
        )

    def run_with_documents(
        self,
        *,
        assistant_evaluations: list[AgentEvaluation],
        job_description_text: str,
        cv_candidate_text: str,
        cv_client_text: str,
        interview_transcript_text: str,
    ) -> MiddleManagementEvaluation:
        assistants_json = json.dumps([e.model_dump() for e in assistant_evaluations], ensure_ascii=False)

        results: list[MiddleManagementEvaluation] = []
        for prompt_path in self.prompt_paths:
            template = self._load_prompt(prompt_path)
            prompt = (
                template.replace("{{assistants_evaluations_json}}", assistants_json)
                .replace("{{job_description_text}}", job_description_text)
                .replace("{{cv_candidate_text}}", cv_candidate_text)
                .replace("{{cv_client_text}}", cv_client_text)
                .replace("{{interview_transcript_text}}", interview_transcript_text)
            )
            payload = self.llm_service.generate_json(prompt=prompt, context="")
            results.append(self._coerce_middle_payload(payload))

        if not results:
            return MiddleManagementEvaluation(
                score_consolidated=0.0,
                conflicts=[],
                critical_questions=[],
                analysis="(MVP) Sem avaliacao de middle management.",
            )

        # Consolida de forma deterministica: score media; conflitos/questoes uniao; analise concatenada.
        avg_score = sum(r.score_consolidated for r in results) / len(results)
        conflicts: list[str] = []
        critical_questions: list[str] = []
        analysis_parts: list[str] = []
        for r in results:
            conflicts.extend(r.conflicts)
            critical_questions.extend(r.critical_questions)
            analysis_parts.append(r.analysis)

        # Dedup preservando ordem.
        def _dedupe(items: list[str]) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []
            for it in items:
                if it in seen:
                    continue
                seen.add(it)
                out.append(it)
            return out

        return MiddleManagementEvaluation(
            score_consolidated=avg_score,
            conflicts=_dedupe([c for c in conflicts if c]),
            critical_questions=_dedupe([q for q in critical_questions if q]),
            analysis="\n\n".join([p for p in analysis_parts if p.strip()]) or "(Sem analise informada.)",
        )

    @staticmethod
    def _coerce_middle_payload(payload: dict) -> MiddleManagementEvaluation:
        """
        Compatibilidade:
        - Formato antigo (score_consolidated/conflicts/critical_questions/analysis).
        - Formato issue #19 (score/summary/key_strengths/key_gaps/risks/conflicts_detected/follow_up_questions/confidence).
        """
        if "score_consolidated" in payload:
            return MiddleManagementEvaluation(**payload)

        if "score" in payload:
            summary = str(payload.get("summary") or "")
            key_strengths = list(payload.get("key_strengths") or [])
            key_gaps = list(payload.get("key_gaps") or [])
            risks = list(payload.get("risks") or [])
            conflicts_detected = list(payload.get("conflicts_detected") or payload.get("conflicts") or [])
            follow_up_questions = list(payload.get("follow_up_questions") or payload.get("critical_questions") or [])

            analysis_parts: list[str] = []
            if summary:
                analysis_parts.append(summary)
            if key_strengths:
                analysis_parts.append("Key strengths:\n" + "\n".join(f"- {s}" for s in key_strengths))
            if key_gaps:
                analysis_parts.append("Key gaps:\n" + "\n".join(f"- {g}" for g in key_gaps))
            if risks:
                analysis_parts.append("Riscos:\n" + "\n".join(f"- {r}" for r in risks))

            return MiddleManagementEvaluation(
                score_consolidated=float(payload["score"]),
                conflicts=[str(x) for x in conflicts_detected],
                critical_questions=[str(x) for x in follow_up_questions],
                analysis="\n\n".join(analysis_parts) or "(Sem analise informada.)",
            )

        raise ValueError(f"Formato de payload inesperado para middle management: chaves={sorted(payload.keys())}")

    def _load_prompt(self, prompt_path: str | Path) -> str:
        return Path(prompt_path).read_text(encoding="utf-8", errors="ignore")


class CTOFinalizer:
    def __init__(self, *, llm_service: object, prompts_root: str | Path = "prompts") -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)
        self.prompt_path = str(self.prompts_root / "c_level" / "generic_delivery_manager.md")

    def run(
        self,
        *,
        job_description_text: str,
        cv_candidate_text: str,
        cv_client_text: str,
        interview_transcript_text: str,
        middle_management_evaluation: MiddleManagementEvaluation,
    ) -> CTOFinalEvaluation:
        template = self._load_prompt(self.prompt_path)
        middle_json = json.dumps(middle_management_evaluation.model_dump(), ensure_ascii=False)
        prompt = (
            template.replace("{{job_description_text}}", job_description_text)
            .replace("{{cv_candidate_text}}", cv_candidate_text)
            .replace("{{cv_client_text}}", cv_client_text)
            .replace("{{interview_transcript_text}}", interview_transcript_text)
            .replace("{{middle_management_json}}", middle_json)
        )

        payload = self.llm_service.generate_json(prompt=prompt, context="")
        return self._coerce_cto_payload(payload)

    def _load_prompt(self, prompt_path: str | Path) -> str:
        return Path(prompt_path).read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _decision_to_final_indication(final_decision: str) -> FinalIndication:
        d = (final_decision or "").strip().upper()
        if "REPROVAR" in d:
            return FinalIndication.Reprovar
        if "COM_RESSALVAS" in d or "COM RESSALVAS" in d:
            return FinalIndication.AprovarComRessalvas
        # APROVADO / APROVAR (fallback)
        return FinalIndication.Aprovar

    @staticmethod
    def _score_to_final_rating(score_final: float) -> FinalRating:
        # Faixas simples para manter o report funcionando mesmo sem o LLM retornar final_rating.
        s = float(score_final)
        if s < 3.0:
            return FinalRating.Estagiario
        if s < 5.5:
            return FinalRating.Junior
        if s < 7.5:
            return FinalRating.Pleno
        if s < 9.0:
            return FinalRating.Senior
        return FinalRating.Especialista

    def _coerce_cto_payload(self, payload: dict) -> CTOFinalEvaluation:
        """
        Compatibilidade:
        - Formato antigo (final_rating/final_indication/score_final/risks/observations).
        - Formato issue #19 (final_decision/final_score/executive_summary/.../recommendations/confidence).
        """
        if "final_rating" in payload and "final_indication" in payload:
            return CTOFinalEvaluation(**payload)

        if "final_decision" in payload and "final_score" in payload:
            score_final = float(payload["final_score"])
            risks = list(payload.get("risks") or [])

            final_indication = self._decision_to_final_indication(str(payload.get("final_decision") or ""))
            final_rating = self._score_to_final_rating(score_final)

            executive_summary = str(payload.get("executive_summary") or "")
            recommendations = payload.get("recommendations") or []
            if isinstance(recommendations, list):
                recommendations_text = "\n".join(f"- {str(x)}" for x in recommendations if x)
            else:
                recommendations_text = f"- {str(recommendations)}" if recommendations else ""

            client_benchmark = payload.get("client_benchmark") or {}
            gap_level = client_benchmark.get("gap_level") if isinstance(client_benchmark, dict) else None
            notes = client_benchmark.get("notes") if isinstance(client_benchmark, dict) else None
            client_benchmark_text = ""
            if gap_level or notes:
                client_benchmark_text = f"Benchmark do cliente - gap_level: {gap_level or 'N/A'}\nNotas: {notes or 'N/A'}"

            def _dump_obj(obj: object) -> str:
                if obj is None:
                    return ""
                if isinstance(obj, str):
                    return obj
                try:
                    return json.dumps(obj, ensure_ascii=False)
                except TypeError:
                    return str(obj)

            strategic_analysis = _dump_obj(payload.get("strategic_analysis"))
            technical_analysis = _dump_obj(payload.get("technical_analysis"))
            behavioral_analysis = _dump_obj(payload.get("behavioral_analysis"))

            observations_parts: list[str] = []
            if executive_summary:
                observations_parts.append("Resumo executivo:\n" + executive_summary)
            if strategic_analysis:
                observations_parts.append("Analise estrategica:\n" + strategic_analysis)
            if technical_analysis:
                observations_parts.append("Analise tecnica:\n" + technical_analysis)
            if behavioral_analysis:
                observations_parts.append("Analise comportamental:\n" + behavioral_analysis)
            if client_benchmark_text:
                observations_parts.append(client_benchmark_text)
            if recommendations_text:
                observations_parts.append("Recomendacoes:\n" + recommendations_text)

            observations = "\n\n".join([p for p in observations_parts if p.strip()]) or "(Sem observacoes informadas.)"

            return CTOFinalEvaluation(
                final_rating=final_rating,
                score_final=score_final,
                final_indication=final_indication,
                risks=[str(r) for r in risks],
                observations=observations,
            )

        raise ValueError(f"Formato de payload inesperado para CTO: chaves={sorted(payload.keys())}")

