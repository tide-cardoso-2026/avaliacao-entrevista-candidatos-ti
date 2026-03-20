"""Camadas 2 e 3: consolidação middle management, divergências e laudo final do CTO."""

from __future__ import annotations

import json
import logging
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.core.config import settings
from app.core.cto_heuristic import heuristic_final_indication
from app.core.pipeline_contract import compute_weighted_score_with_agent_weights
from app.core.protocols import LLMService
from app.models.schemas import (
    AgentEvaluation,
    CTOLayerBlock,
    CTORiskItem,
    CTOFinalEvaluation,
    DivergenceFlag,
    FinalIndication,
    FinalRating,
    MiddleManagementEvaluation,
    MiddleRiskItem,
)

log = logging.getLogger(__name__)

DIVERGENCE_THRESHOLD = 2.0
CRITICAL_DIVERGENCE_THRESHOLD = 3.5

# Ordem alinhada a `prompt_paths` (tech → product → sre).
MANAGER_ROLES: list[str] = ["tech_manager", "product_manager", "sre_manager"]

_HIRE_PRIORITY = {"no_hire": 0, "hire_with_risks": 1, "hire": 2}


def _normalize_structured_risks(raw: object) -> list[MiddleRiskItem]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    out: list[MiddleRiskItem] = []
    for item in raw:
        if isinstance(item, MiddleRiskItem):
            out.append(item)
        elif isinstance(item, dict):
            desc = str(item.get("description") or item.get("text") or "").strip()
            if not desc:
                continue
            out.append(MiddleRiskItem.model_validate({"description": desc, "severity": item.get("severity", "medium")}))
        elif isinstance(item, str) and item.strip():
            out.append(MiddleRiskItem(description=item.strip(), severity="medium"))
    return out


def _merge_hire_recommendations(recs: list[str | None]) -> str | None:
    norm = [r for r in recs if r]
    if not norm:
        return None
    return min(norm, key=lambda x: _HIRE_PRIORITY.get(x, 99))


def _sync_hire_final(hire: object, final: object) -> tuple[object, object]:
    h = hire
    f = final
    if h in (None, "") and f not in (None, ""):
        h = f
    if f in (None, "") and h not in (None, ""):
        f = h
    return h, f


def _dedupe_risk_items(items: list[MiddleRiskItem]) -> list[MiddleRiskItem]:
    seen: set[tuple[str, str]] = set()
    out: list[MiddleRiskItem] = []
    for r in items:
        key = (r.description.strip().lower(), r.severity)
        if not r.description.strip() or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _dedupe_str_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if not it or it in seen:
            continue
        seen.add(it)
        out.append(it)
    return out


def _dump_obj_for_layer(obj: object) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    try:
        return json.dumps(obj, ensure_ascii=False)
    except TypeError:
        return str(obj)


def _coerce_cto_layer(raw: object) -> CTOLayerBlock:
    if raw is None:
        return CTOLayerBlock()
    if isinstance(raw, dict):
        if "assessment" in raw or "evidence" in raw:
            ev = raw.get("evidence")
            ev_list = [str(x) for x in ev] if isinstance(ev, list) else []
            return CTOLayerBlock(
                assessment=str(raw.get("assessment") or ""),
                evidence=ev_list,
            )
        if not raw:
            return CTOLayerBlock()
        return CTOLayerBlock(assessment=_dump_obj_for_layer(raw))
    return CTOLayerBlock(assessment=_dump_obj_for_layer(raw))


def _normalize_cto_risks(raw: object) -> list[CTORiskItem]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    out: list[CTORiskItem] = []
    for item in raw:
        if isinstance(item, CTORiskItem):
            out.append(item)
        elif isinstance(item, dict):
            out.append(CTORiskItem.model_validate(item))
        elif isinstance(item, str) and item.strip():
            out.append(CTORiskItem(description=item.strip()))
    return out


def _cto_layer_observation_block(title: str, layer: CTOLayerBlock) -> str:
    if not layer.assessment.strip() and not layer.evidence:
        return ""
    parts = [f"{title}:\n{layer.assessment.strip()}"]
    if layer.evidence:
        parts.append("Evidencias:\n" + "\n".join(f"- {e}" for e in layer.evidence))
    return "\n".join(parts)


# Confidence-weighted average: sum(score*confidence) / sum(confidence).
def compute_weighted_score(evaluations: list[AgentEvaluation]) -> float:
    total_weight = sum(e.confidence for e in evaluations)
    if total_weight == 0:
        return 0.0
    return round(sum(e.score * e.confidence for e in evaluations) / total_weight, 2)


# Detect pairs of agents with significant score disagreement.
def detect_divergences(evaluations: list[AgentEvaluation]) -> list[DivergenceFlag]:
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
        self._middle_principles = self._load_middle_principles()

    # Atalho sem textos de documentos (apenas JSON das avaliações dos assistentes).
    def run(self, *, assistant_evaluations: list[AgentEvaluation]) -> MiddleManagementEvaluation:
        return self.run_with_documents(
            assistant_evaluations=assistant_evaluations,
            job_description_text="",
            cv_candidate_text="",
            cv_client_text="",
            interview_transcript_text="",
        )

    # Executa cada prompt de manager em paralelo, depois consolida (merge + opcional pré-CTO).
    def run_with_documents(
        self,
        *,
        assistant_evaluations: list[AgentEvaluation],
        job_description_text: str,
        cv_candidate_text: str,
        cv_client_text: str,
        interview_transcript_text: str,
    ) -> MiddleManagementEvaluation:
        results = self.run_managers_parallel(
            assistant_evaluations=assistant_evaluations,
            job_description_text=job_description_text,
            cv_candidate_text=cv_candidate_text,
            cv_client_text=cv_client_text,
            interview_transcript_text=interview_transcript_text,
        )
        return self.finalize_middle_managers(results, assistant_evaluations)

    # Rodada de managers (LLM em paralelo): tech, product, sre — ou um único generic_consolidator.
    def run_managers_parallel(
        self,
        *,
        assistant_evaluations: list[AgentEvaluation],
        job_description_text: str,
        cv_candidate_text: str,
        cv_client_text: str,
        interview_transcript_text: str,
    ) -> list[MiddleManagementEvaluation]:
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
        weighted_by_role = compute_weighted_score_with_agent_weights(assistant_evaluations)
        log.debug(
            "Running middle management (%d prompt(s) parallel), weighted_score=%.2f, "
            "weighted_by_agent_weights=%.2f",
            len(self.prompt_paths), weighted_score, weighted_by_role,
        )

        def _run_one(prompt_path: Path) -> MiddleManagementEvaluation:
            template = self._load_prompt(prompt_path)
            prompt = (
                template.replace("{{assistants_evaluations_json}}", assistants_json + divergence_summary)
                .replace("{{job_description_text}}", job_description_text)
                .replace("{{cv_candidate_text}}", cv_candidate_text)
                .replace("{{cv_client_text}}", cv_client_text)
                .replace("{{interview_transcript_text}}", interview_transcript_text)
                .replace("{{scoring_rubric}}", self._rubric)
                .replace("{{middle_principles}}", self._middle_principles)
            )
            if "{{scoring_rubric}}" not in template:
                prompt = self._rubric + "\n\n" + prompt
            if "{{middle_principles}}" not in template and self._middle_principles:
                prompt = self._middle_principles + "\n\n" + prompt
            payload = self.llm_service.generate_json(prompt=prompt, context="", layer="middle")
            return self._coerce_middle_payload(payload)

        workers = max(1, len(self.prompt_paths))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_one, p) for p in self.prompt_paths]
            return [f.result() for f in futures]

    # Merge determinístico + divergências; opcional LLM pré-CTO com `middle_managers_json`.
    def finalize_middle_managers(
        self,
        results: list[MiddleManagementEvaluation],
        assistant_evaluations: list[AgentEvaluation],
    ) -> MiddleManagementEvaluation:
        divergence_flags = list(detect_divergences(assistant_evaluations))
        if not results:
            return MiddleManagementEvaluation(
                score_consolidated=0.0,
                conflicts=[],
                critical_questions=[],
                divergence_flags=divergence_flags,
                analysis="(Sem avaliacao de middle management.)",
            )

        merged = self._merge_manager_results(results, divergence_flags)
        if (
            settings.ENABLE_PRE_CTO_CONSOLIDATOR
            and len(self.prompt_paths) >= 3
            and len(results) >= 3
        ):
            try:
                return self._run_pre_cto_consolidator_llm(
                    assistant_evaluations=assistant_evaluations,
                    manager_evaluations=results,
                    merged_fallback=merged,
                )
            except Exception:
                log.exception("Pre-CTO consolidator LLM failed; using deterministic merge")
                return merged
        return merged

    def _merge_manager_results(
        self,
        results: list[MiddleManagementEvaluation],
        divergence_flags: list[DivergenceFlag],
    ) -> MiddleManagementEvaluation:
        manager_scores = [r.score_consolidated for r in results]
        manager_confidences = [r.confidence for r in results]

        total_conf = sum(manager_confidences)
        if total_conf > 0:
            consolidated_score = round(
                sum(s * c for s, c in zip(manager_scores, manager_confidences, strict=True)) / total_conf, 2
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
        key_strengths: list[str] = []
        key_gaps: list[str] = []
        missing_evidence: list[str] = []
        structured_risk_acc: list[MiddleRiskItem] = []
        hire_recs: list[str | None] = []
        final_recs: list[str | None] = []
        for r in results:
            conflicts.extend(r.conflicts)
            critical_questions.extend(r.critical_questions)
            analysis_parts.append(r.analysis)
            key_strengths.extend(r.key_strengths)
            key_gaps.extend(r.key_gaps)
            missing_evidence.extend(r.missing_evidence)
            structured_risk_acc.extend(r.structured_risks)
            hire_recs.append(r.hire_recommendation)
            final_recs.append(r.final_recommendation)

        avg_confidence = round(sum(manager_confidences) / len(manager_confidences), 2) if manager_confidences else 1.0

        merged_hire = _merge_hire_recommendations(hire_recs)
        merged_final = _merge_hire_recommendations(final_recs)
        if merged_final is None and merged_hire is not None:
            merged_final = merged_hire
        if merged_hire is None and merged_final is not None:
            merged_hire = merged_final

        consolidated = MiddleManagementEvaluation(
            score_consolidated=consolidated_score,
            confidence=avg_confidence,
            conflicts=_dedupe_str_list([c for c in conflicts if c]),
            critical_questions=_dedupe_str_list([q for q in critical_questions if q]),
            divergence_flags=divergence_flags,
            key_strengths=_dedupe_str_list([s for s in key_strengths if s]),
            key_gaps=_dedupe_str_list([g for g in key_gaps if g]),
            missing_evidence=_dedupe_str_list([m for m in missing_evidence if m]),
            structured_risks=_dedupe_risk_items(structured_risk_acc),
            hire_recommendation=merged_hire,
            final_recommendation=merged_final,
            analysis="\n\n".join([p for p in analysis_parts if p.strip()]) or "(Sem analise informada.)",
        )
        log.debug(
            "Middle management merge: score=%.2f, confidence=%.2f, divergences=%d, questions=%d",
            consolidated.score_consolidated, consolidated.confidence,
            len(consolidated.divergence_flags), len(consolidated.critical_questions),
        )
        return consolidated

    def _run_pre_cto_consolidator_llm(
        self,
        *,
        assistant_evaluations: list[AgentEvaluation],
        manager_evaluations: list[MiddleManagementEvaluation],
        merged_fallback: MiddleManagementEvaluation,
    ) -> MiddleManagementEvaluation:
        template = self._load_prompt(self.prompts_root / "middle_management" / "generic_consolidator.md")
        assistants_json = json.dumps([e.model_dump() for e in assistant_evaluations], ensure_ascii=False)
        middle_managers_json = json.dumps([m.model_dump() for m in manager_evaluations], ensure_ascii=False)
        prompt = (
            template.replace("{{assistants_evaluations_json}}", assistants_json)
            .replace("{{middle_managers_json}}", middle_managers_json)
            .replace("{{job_description_text}}", "")
            .replace("{{cv_candidate_text}}", "")
            .replace("{{cv_client_text}}", "")
            .replace("{{interview_transcript_text}}", "")
            .replace("{{scoring_rubric}}", self._rubric)
            .replace("{{middle_principles}}", self._middle_principles)
        )
        if "{{scoring_rubric}}" not in template:
            prompt = self._rubric + "\n\n" + prompt
        if "{{middle_principles}}" not in template and self._middle_principles:
            prompt = self._middle_principles + "\n\n" + prompt
        payload = self.llm_service.generate_json(prompt=prompt, context="", layer="middle")
        out = self._coerce_middle_payload(payload)
        if out.score_consolidated <= 0 and merged_fallback.score_consolidated > 0:
            out = out.model_copy(update={"score_consolidated": merged_fallback.score_consolidated})
        return out

    @staticmethod
    # Normaliza resposta do LLM (schema novo ou legado com `score`/`summary`) para o modelo Pydantic.
    def _coerce_middle_payload(payload: dict) -> MiddleManagementEvaluation:
        confidence = payload.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(confidence))) if confidence is not None else 1.0
        except (ValueError, TypeError):
            confidence = 1.0

        allowed = set(MiddleManagementEvaluation.model_fields.keys())

        if "score_consolidated" in payload:
            p = dict(payload)
            p.pop("agent", None)
            p["confidence"] = confidence
            p.setdefault("divergence_flags", [])
            risks_raw = p.pop("risks", None)
            sr_existing = p.get("structured_risks")
            if sr_existing:
                p["structured_risks"] = _normalize_structured_risks(sr_existing)
            elif risks_raw is not None:
                p["structured_risks"] = _normalize_structured_risks(risks_raw)
            else:
                p.setdefault("structured_risks", [])
            cleaned = {k: v for k, v in p.items() if k in allowed}
            h_s, f_s = _sync_hire_final(cleaned.get("hire_recommendation"), cleaned.get("final_recommendation"))
            cleaned["hire_recommendation"] = h_s
            cleaned["final_recommendation"] = f_s
            return MiddleManagementEvaluation.model_validate(cleaned)

        if "score" in payload:
            summary = str(payload.get("summary") or "")
            key_strengths = list(payload.get("key_strengths") or [])
            key_gaps = list(payload.get("key_gaps") or [])
            conflicts_detected = list(payload.get("conflicts_detected") or payload.get("conflicts") or [])
            follow_up_questions = list(payload.get("follow_up_questions") or payload.get("critical_questions") or [])
            missing_evidence = list(payload.get("missing_evidence") or [])
            structured_risks = _normalize_structured_risks(payload.get("risks"))

            analysis_parts: list[str] = []
            if summary:
                analysis_parts.append(summary)
            if key_strengths:
                analysis_parts.append("Key strengths:\n" + "\n".join(f"- {s}" for s in key_strengths))
            if key_gaps:
                analysis_parts.append("Key gaps:\n" + "\n".join(f"- {g}" for g in key_gaps))
            if structured_risks:
                analysis_parts.append(
                    "Riscos:\n"
                    + "\n".join(f"- [{r.severity}] {r.description}" for r in structured_risks)
                )
            if missing_evidence:
                analysis_parts.append(
                    "Evidencias ausentes:\n" + "\n".join(f"- {m}" for m in missing_evidence)
                )

            h_raw, f_raw = _sync_hire_final(payload.get("hire_recommendation"), payload.get("final_recommendation"))
            return MiddleManagementEvaluation.model_validate(
                {
                    "score_consolidated": float(payload["score"]),
                    "confidence": confidence,
                    "conflicts": [str(x) for x in conflicts_detected],
                    "critical_questions": [str(x) for x in follow_up_questions],
                    "divergence_flags": [],
                    "key_strengths": [str(x) for x in key_strengths],
                    "key_gaps": [str(x) for x in key_gaps],
                    "missing_evidence": [str(x) for x in missing_evidence],
                    "structured_risks": [r.model_dump() for r in structured_risks],
                    "hire_recommendation": h_raw,
                    "final_recommendation": f_raw,
                    "calibration_notes": payload.get("calibration_notes"),
                    "analysis": "\n\n".join(analysis_parts) or "(Sem analise informada.)",
                }
            )

        raise ValueError(f"Unexpected middle management payload format: keys={sorted(payload.keys())}")

    # Lê arquivo de prompt de middle management.
    def _load_prompt(self, prompt_path: str | Path) -> str:
        return Path(prompt_path).read_text(encoding="utf-8", errors="ignore")

    # Carrega rubrica compartilhada para os prompts de middle.
    def _load_rubric(self) -> str:
        rubric_path = self.prompts_root / "shared" / "scoring_rubric.md"
        if rubric_path.exists():
            return rubric_path.read_text(encoding="utf-8", errors="ignore")
        return ""

    # Principios compartilhados (middle management como ponte execucao/estrategia).
    def _load_middle_principles(self) -> str:
        path = self.prompts_root / "shared" / "middle_management_principles.md"
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore")
        return ""


# Última camada: síntese C-level a partir dos textos e das avaliações anteriores.
class CTOFinalizer:

    # Fixa prompt do delivery manager genérico e rubrica.
    def __init__(self, *, llm_service: LLMService, prompts_root: str | Path = "prompts") -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)
        self.prompt_path = str(self.prompts_root / "c_level" / "generic_delivery_manager.md")
        self._rubric = self._load_rubric()
        self._cto_principles = self._load_cto_decision_principles()

    # Monta prompt com documentos + middle + assistentes e devolve `CTOFinalEvaluation`.
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
            .replace("{{cto_decision_principles}}", self._cto_principles)
        )
        if "{{scoring_rubric}}" not in template:
            prompt = self._rubric + "\n\n" + prompt
        if "{{cto_decision_principles}}" not in template and self._cto_principles:
            prompt = self._cto_principles + "\n\n" + prompt

        log.debug("Running CTO final evaluation")
        payload = self.llm_service.generate_json(prompt=prompt, context="", layer="cto")
        result = self._coerce_cto_payload(payload)
        log.debug(
            "CTO result: score=%.2f, rating=%s, indication=%s, confidence=%.2f",
            result.score_final, result.final_rating.value,
            result.final_indication.value, result.confidence,
        )
        hint = heuristic_final_indication(result.score_final, result.risks)
        if hint != result.final_indication:
            log.warning(
                "CTO heuristic suggests %s; LLM indication is %s (score=%.2f)",
                hint.value, result.final_indication.value, result.score_final,
            )
            note = (
                "\n\n[Heuristica baseline] Indicacao objetiva (score + riscos): "
                f"{hint.value}. Comparar com a indicacao do modelo acima."
            )
            result = result.model_copy(update={"observations": result.observations + note})
        return result

    # Lê template do prompt C-level a partir do caminho configurado.
    def _load_prompt(self, prompt_path: str | Path) -> str:
        return Path(prompt_path).read_text(encoding="utf-8", errors="ignore")

    # Rubrica opcional para o laudo do CTO.
    def _load_rubric(self) -> str:
        rubric_path = self.prompts_root / "shared" / "scoring_rubric.md"
        if rubric_path.exists():
            return rubric_path.read_text(encoding="utf-8", errors="ignore")
        return ""

    def _load_cto_decision_principles(self) -> str:
        path = self.prompts_root / "shared" / "cto_decision_principles.md"
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore")
        return ""

    @staticmethod
    # Mapeia texto APROVAR_/REPROVAR do modelo para enum `FinalIndication`.
    def _decision_to_final_indication(final_decision: str) -> FinalIndication:
        d = (final_decision or "").strip().upper()
        if "REPROVAR" in d:
            return FinalIndication.Reprovar
        if "COM_RESSALVAS" in d or "COM RESSALVAS" in d:
            return FinalIndication.AprovarComRessalvas
        return FinalIndication.Aprovar

    @staticmethod
    # Converte nota numérica em faixa `FinalRating` (estagiário … especialista).
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

    # Aceita payload já no schema final ou formato legado `final_decision`/`final_score`.
    def _coerce_cto_payload(self, payload: dict) -> CTOFinalEvaluation:
        confidence = payload.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(confidence))) if confidence is not None else 1.0
        except (ValueError, TypeError):
            confidence = 1.0

        allowed = set(CTOFinalEvaluation.model_fields.keys())

        if "final_rating" in payload and "final_indication" in payload:
            p = dict(payload)
            p["confidence"] = confidence
            p["strategic_analysis"] = _coerce_cto_layer(p.get("strategic_analysis"))
            p["tactical_analysis"] = _coerce_cto_layer(p.get("tactical_analysis"))
            p["operational_analysis"] = _coerce_cto_layer(p.get("operational_analysis"))
            p["risks"] = _normalize_cto_risks(p.get("risks"))
            to = p.get("tradeoffs")
            p["tradeoffs"] = [str(x) for x in to] if isinstance(to, list) else []
            cleaned = {k: v for k, v in p.items() if k in allowed}
            return CTOFinalEvaluation.model_validate(cleaned)

        if "final_decision" in payload and "final_score" in payload:
            score_final = float(payload["final_score"])

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

            strategic = _coerce_cto_layer(payload.get("strategic_analysis"))
            tactical = _coerce_cto_layer(payload.get("tactical_analysis"))
            operational = _coerce_cto_layer(payload.get("operational_analysis"))
            if not tactical.assessment and not tactical.evidence:
                tac_fb = _coerce_cto_layer(payload.get("technical_analysis"))
                if tac_fb.assessment or tac_fb.evidence:
                    tactical = tac_fb
            if not operational.assessment and not operational.evidence:
                op_fb = _coerce_cto_layer(payload.get("behavioral_analysis"))
                if op_fb.assessment or op_fb.evidence:
                    operational = op_fb

            tradeoffs = [str(x) for x in (payload.get("tradeoffs") or []) if x]
            risks = _normalize_cto_risks(payload.get("risks"))

            observations_parts: list[str] = []
            if executive_summary:
                observations_parts.append("Resumo executivo:\n" + executive_summary)
            eb = _cto_layer_observation_block("Analise estrategica", strategic)
            if eb:
                observations_parts.append(eb)
            tb = _cto_layer_observation_block("Analise tatica", tactical)
            if tb:
                observations_parts.append(tb)
            ob = _cto_layer_observation_block("Analise operacional", operational)
            if ob:
                observations_parts.append(ob)
            if client_benchmark_text:
                observations_parts.append(client_benchmark_text)
            if tradeoffs:
                observations_parts.append("Trade-offs:\n" + "\n".join(f"- {t}" for t in tradeoffs))
            if risks:
                observations_parts.append(
                    "Riscos priorizados:\n"
                    + "\n".join(
                        f"- [impacto {r.impact}, prob. {r.probability}] {r.description}" for r in risks
                    )
                )
            if recommendations_text:
                observations_parts.append("Recomendacoes:\n" + recommendations_text)

            observations = "\n\n".join([p for p in observations_parts if p.strip()]) or "(Sem observacoes informadas.)"

            return CTOFinalEvaluation(
                final_rating=final_rating,
                score_final=score_final,
                final_indication=final_indication,
                strategic_analysis=strategic,
                tactical_analysis=tactical,
                operational_analysis=operational,
                tradeoffs=tradeoffs,
                risks=risks,
                observations=observations,
                confidence=confidence,
            )

        raise ValueError(f"Unexpected CTO payload format: keys={sorted(payload.keys())}")
