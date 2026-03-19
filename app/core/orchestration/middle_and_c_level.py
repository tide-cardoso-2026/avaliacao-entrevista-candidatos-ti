from __future__ import annotations

import json
import logging
import statistics
from pathlib import Path

from app.core.protocols import LLMService
from app.models.schemas import (
    AgentEvaluation,
    CTOFinalEvaluation,
    DivergenceFlag,
    FinalIndication,
    FinalRating,
    MiddleManagementEvaluation,
)

log = logging.getLogger(__name__)

DIVERGENCE_THRESHOLD = 2.0
CRITICAL_DIVERGENCE_THRESHOLD = 3.5


def compute_weighted_score(evaluations: list[AgentEvaluation]) -> float:
    """Confidence-weighted average: sum(score*confidence) / sum(confidence)."""
    total_weight = sum(e.confidence for e in evaluations)
    if total_weight == 0:
        return 0.0
    return round(sum(e.score * e.confidence for e in evaluations) / total_weight, 2)


def detect_divergences(evaluations: list[AgentEvaluation]) -> list[DivergenceFlag]:
    """Detect pairs of agents with significant score disagreement."""
    if len(evaluations) < 2:
        return []

    flags: list[DivergenceFlag] = []
    scores = [e.score for e in evaluations]
    global_spread = max(scores) - min(scores)

    if global_spread >= CRITICAL_DIVERGENCE_THRESHOLD:
        top = max(evaluations, key=lambda e: e.score)
        bottom = min(evaluations, key=lambda e: e.score)
        flags.append(DivergenceFlag(
            agents_involved=[top.agent_name, bottom.agent_name],
            score_spread=round(global_spread, 2),
            description=(
                f"Divergencia critica: {top.agent_name} ({top.score}) vs "
                f"{bottom.agent_name} ({bottom.score}). Spread={global_spread:.1f}"
            ),
        ))

    high_conf = [e for e in evaluations if e.confidence >= 0.7]
    if len(high_conf) >= 2:
        hc_scores = [e.score for e in high_conf]
        stdev = statistics.stdev(hc_scores) if len(hc_scores) > 1 else 0
        if stdev >= 1.5:
            sorted_hc = sorted(high_conf, key=lambda e: e.score)
            flags.append(DivergenceFlag(
                agents_involved=[sorted_hc[0].agent_name, sorted_hc[-1].agent_name],
                score_spread=round(sorted_hc[-1].score - sorted_hc[0].score, 2),
                description=(
                    f"Alta variancia entre avaliadores confiaveis (stdev={stdev:.2f}): "
                    f"{sorted_hc[0].agent_name} ({sorted_hc[0].score}) vs "
                    f"{sorted_hc[-1].agent_name} ({sorted_hc[-1].score})"
                ),
            ))

    return flags


class MiddleManagementConsolidator:
    def __init__(self, *, llm_service: LLMService, prompts_root: str | Path = "prompts") -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)
        self.prompt_paths: list[Path] = [
            self.prompts_root / "middle_management" / "tech_manager.md",
            self.prompts_root / "middle_management" / "product_manager.md",
            self.prompts_root / "middle_management" / "sre_manager.md",
        ]
        if not all(p.exists() for p in self.prompt_paths):
            self.prompt_paths = [self.prompts_root / "middle_management" / "generic_consolidator.md"]

        self._rubric = self._load_rubric()

    def run(self, *, assistant_evaluations: list[AgentEvaluation]) -> MiddleManagementEvaluation:
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

        divergence_flags = detect_divergences(assistant_evaluations)
        if divergence_flags:
            log.warning("Divergences detected: %d flag(s)", len(divergence_flags))
            for flag in divergence_flags:
                log.warning("  -> %s", flag.description)

        divergence_summary = ""
        if divergence_flags:
            divergence_summary = "\n\nDIVERGENCIAS DETECTADAS AUTOMATICAMENTE:\n" + "\n".join(
                f"- {f.description}" for f in divergence_flags
            )

        weighted_score = compute_weighted_score(assistant_evaluations)
        log.info(
            "Running middle management consolidation (%d prompt(s)), weighted_score=%.2f",
            len(self.prompt_paths), weighted_score,
        )

        results: list[MiddleManagementEvaluation] = []
        for prompt_path in self.prompt_paths:
            template = self._load_prompt(prompt_path)
            prompt = (
                template.replace("{{assistants_evaluations_json}}", assistants_json + divergence_summary)
                .replace("{{job_description_text}}", job_description_text)
                .replace("{{cv_candidate_text}}", cv_candidate_text)
                .replace("{{cv_client_text}}", cv_client_text)
                .replace("{{interview_transcript_text}}", interview_transcript_text)
                .replace("{{scoring_rubric}}", self._rubric)
            )
            if "{{scoring_rubric}}" not in template:
                prompt = self._rubric + "\n\n" + prompt
            payload = self.llm_service.generate_json(prompt=prompt, context="")
            results.append(self._coerce_middle_payload(payload))

        if not results:
            return MiddleManagementEvaluation(
                score_consolidated=0.0,
                conflicts=[],
                critical_questions=[],
                divergence_flags=divergence_flags,
                analysis="(Sem avaliacao de middle management.)",
            )

        manager_scores = [r.score_consolidated for r in results]
        manager_confidences = [r.confidence for r in results]

        total_conf = sum(manager_confidences)
        if total_conf > 0:
            consolidated_score = round(
                sum(s * c for s, c in zip(manager_scores, manager_confidences)) / total_conf, 2
            )
        else:
            consolidated_score = round(sum(manager_scores) / len(manager_scores), 2)

        if len(manager_scores) > 1:
            mgr_spread = max(manager_scores) - min(manager_scores)
            if mgr_spread >= DIVERGENCE_THRESHOLD:
                divergence_flags.append(DivergenceFlag(
                    agents_involved=["middle_managers"],
                    score_spread=round(mgr_spread, 2),
                    description=f"Divergencia entre middle managers: scores={manager_scores}, spread={mgr_spread:.1f}",
                ))
                log.warning("Middle manager divergence: scores=%s, spread=%.1f", manager_scores, mgr_spread)

        conflicts: list[str] = []
        critical_questions: list[str] = []
        analysis_parts: list[str] = []
        for r in results:
            conflicts.extend(r.conflicts)
            critical_questions.extend(r.critical_questions)
            analysis_parts.append(r.analysis)

        def _dedupe(items: list[str]) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []
            for it in items:
                if it in seen:
                    continue
                seen.add(it)
                out.append(it)
            return out

        avg_confidence = round(sum(manager_confidences) / len(manager_confidences), 2) if manager_confidences else 1.0

        consolidated = MiddleManagementEvaluation(
            score_consolidated=consolidated_score,
            confidence=avg_confidence,
            conflicts=_dedupe([c for c in conflicts if c]),
            critical_questions=_dedupe([q for q in critical_questions if q]),
            divergence_flags=divergence_flags,
            analysis="\n\n".join([p for p in analysis_parts if p.strip()]) or "(Sem analise informada.)",
        )
        log.info(
            "Middle management result: score=%.2f, confidence=%.2f, divergences=%d, questions=%d",
            consolidated.score_consolidated, consolidated.confidence,
            len(consolidated.divergence_flags), len(consolidated.critical_questions),
        )
        return consolidated

    @staticmethod
    def _coerce_middle_payload(payload: dict) -> MiddleManagementEvaluation:
        confidence = payload.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(confidence))) if confidence is not None else 1.0
        except (ValueError, TypeError):
            confidence = 1.0

        if "score_consolidated" in payload:
            payload = dict(payload)
            payload["confidence"] = confidence
            payload.setdefault("divergence_flags", [])
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
                confidence=confidence,
                conflicts=[str(x) for x in conflicts_detected],
                critical_questions=[str(x) for x in follow_up_questions],
                divergence_flags=[],
                analysis="\n\n".join(analysis_parts) or "(Sem analise informada.)",
            )

        raise ValueError(f"Unexpected middle management payload format: keys={sorted(payload.keys())}")

    def _load_prompt(self, prompt_path: str | Path) -> str:
        return Path(prompt_path).read_text(encoding="utf-8", errors="ignore")

    def _load_rubric(self) -> str:
        rubric_path = self.prompts_root / "shared" / "scoring_rubric.md"
        if rubric_path.exists():
            return rubric_path.read_text(encoding="utf-8", errors="ignore")
        return ""


class CTOFinalizer:
    def __init__(self, *, llm_service: LLMService, prompts_root: str | Path = "prompts") -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)
        self.prompt_path = str(self.prompts_root / "c_level" / "generic_delivery_manager.md")
        self._rubric = self._load_rubric()

    def run(
        self,
        *,
        job_description_text: str,
        cv_candidate_text: str,
        cv_client_text: str,
        interview_transcript_text: str,
        middle_management_evaluation: MiddleManagementEvaluation,
        assistant_evaluations: list[AgentEvaluation],
    ) -> CTOFinalEvaluation:
        template = self._load_prompt(self.prompt_path)
        middle_json = json.dumps(middle_management_evaluation.model_dump(), ensure_ascii=False)
        assistants_json = json.dumps([e.model_dump() for e in assistant_evaluations], ensure_ascii=False)

        prompt = (
            template.replace("{{job_description_text}}", job_description_text)
            .replace("{{cv_candidate_text}}", cv_candidate_text)
            .replace("{{cv_client_text}}", cv_client_text)
            .replace("{{interview_transcript_text}}", interview_transcript_text)
            .replace("{{middle_management_json}}", middle_json)
            .replace("{{assistants_evaluations_json}}", assistants_json)
            .replace("{{scoring_rubric}}", self._rubric)
        )
        if "{{scoring_rubric}}" not in template:
            prompt = self._rubric + "\n\n" + prompt

        log.info("Running CTO final evaluation")
        payload = self.llm_service.generate_json(prompt=prompt, context="")
        result = self._coerce_cto_payload(payload)
        log.info(
            "CTO result: score=%.2f, rating=%s, indication=%s, confidence=%.2f",
            result.score_final, result.final_rating.value,
            result.final_indication.value, result.confidence,
        )
        return result

    def _load_prompt(self, prompt_path: str | Path) -> str:
        return Path(prompt_path).read_text(encoding="utf-8", errors="ignore")

    def _load_rubric(self) -> str:
        rubric_path = self.prompts_root / "shared" / "scoring_rubric.md"
        if rubric_path.exists():
            return rubric_path.read_text(encoding="utf-8", errors="ignore")
        return ""

    @staticmethod
    def _decision_to_final_indication(final_decision: str) -> FinalIndication:
        d = (final_decision or "").strip().upper()
        if "REPROVAR" in d:
            return FinalIndication.Reprovar
        if "COM_RESSALVAS" in d or "COM RESSALVAS" in d:
            return FinalIndication.AprovarComRessalvas
        return FinalIndication.Aprovar

    @staticmethod
    def _score_to_final_rating(score_final: float) -> FinalRating:
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
        confidence = payload.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(confidence))) if confidence is not None else 1.0
        except (ValueError, TypeError):
            confidence = 1.0

        if "final_rating" in payload and "final_indication" in payload:
            payload = dict(payload)
            payload["confidence"] = confidence
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
                confidence=confidence,
            )

        raise ValueError(f"Unexpected CTO payload format: keys={sorted(payload.keys())}")
