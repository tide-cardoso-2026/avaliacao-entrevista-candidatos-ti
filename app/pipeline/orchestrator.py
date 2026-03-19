from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console

from app.core.domain_rules.agent_registry import AgentRegistry
from app.core.orchestration.agent_engine import AgentEngine
from app.core.orchestration.agent_selector import AgentSelector
from app.core.orchestration.middle_and_c_level import CTOFinalizer, MiddleManagementConsolidator
from app.core.protocols import LLMService
from app.models.schemas import AgentDefinition, AgentEvaluation, CTOFinalEvaluation, DocumentSet, MiddleManagementEvaluation
from app.services.parsing_service import ParsingService
from app.services.report_generator import ReportGenerator
from app.utils.file_locator import FileLocator

log = logging.getLogger(__name__)

MAX_DOCUMENT_CHARS = 20_000


@dataclass
class PipelineOrchestrator:
    llm_service: LLMService
    report_generator: ReportGenerator
    parsing_service: ParsingService = field(default_factory=ParsingService)
    file_locator: FileLocator = field(default_factory=FileLocator)
    enable_agent_selection: bool = True
    enable_follow_up_round: bool = True
    enable_deliberation: bool = True

    @dataclass
    class PipelineRunDetails:
        vaga: str
        candidato: str
        assistant_evaluations: list[AgentEvaluation]
        middle_management_evaluation: MiddleManagementEvaluation
        cto_evaluation: CTOFinalEvaluation
        report_path: Optional[str] = None
        agents_selected: int = 0
        agents_total: int = 0
        follow_up_round_executed: bool = False
        deliberation_executed: bool = False

    def run(self, *, vaga: str, candidato: str, client: Optional[str] = None) -> str:
        result = self.run_with_details(vaga=vaga, candidato=candidato, client=client, generate_report=True)
        if not result.report_path:
            raise RuntimeError("Falha ao gerar relatorio no pipeline.")
        return result.report_path

    def run_with_details(
        self,
        *,
        vaga: str,
        candidato: str,
        candidato_display: Optional[str] = None,
        client: Optional[str] = None,
        generate_report: bool = True,
    ) -> PipelineRunDetails:
        console = Console()

        # Step 1: Load
        console.print("[1/8] Carregando dados...")
        log.info("Step 1/8: Loading documents (vaga=%s, candidato=%s)", vaga, candidato)
        documents = self._load_documents(vaga=vaga, candidato=candidato, client=client)

        # Step 2: Preprocess
        console.print("[2/8] Processando inputs...")
        log.info("Step 2/8: Preprocessing documents")
        documents = self._preprocess_documents(documents)

        # Step 3: Agent selection (C)
        all_assistants = AgentRegistry().get_assistants()
        agents_total = len(all_assistants)
        if self.enable_agent_selection:
            console.print("[3/8] Selecionando agentes relevantes para a vaga...")
            log.info("Step 3/8: Dynamic agent selection")
            selector = AgentSelector(llm_service=self.llm_service)
            assistants = selector.select(
                job_description_text=documents.job_description_text,
                all_agents=all_assistants,
            )
            console.print(f"   {len(assistants)}/{agents_total} agentes selecionados")
        else:
            console.print("[3/8] Usando todos os agentes (selecao desativada)")
            assistants = all_assistants
        agents_selected = len(assistants)

        # Step 4: Run assistants
        console.print(f"[4/8] Executando {len(assistants)} Assistentes...")
        log.info("Step 4/8: Running %d specialist assistants", len(assistants))
        agent_engine = AgentEngine(llm_service=self.llm_service)
        evaluations = agent_engine.run_assistants(
            agents=assistants,
            documents=documents,
            on_agent_completed=lambda agent_name, _ev: console.print(f"   - {agent_name} [OK]"),
        )

        # Step 5: Middle management (first round)
        console.print("[5/8] Consolidando Middle Management...")
        log.info("Step 5/8: Middle management consolidation (round 1)")
        mm_consolidator = MiddleManagementConsolidator(llm_service=self.llm_service)
        middle = mm_consolidator.run_with_documents(
            assistant_evaluations=evaluations,
            job_description_text=documents.job_description_text,
            cv_candidate_text=documents.cv_candidate_text,
            cv_client_text=documents.cv_client_text,
            interview_transcript_text=documents.interview_transcript_text,
        )

        # Step 5b: Deliberation between managers (G)
        deliberation_executed = False
        if self.enable_deliberation and len(mm_consolidator.prompt_paths) > 1:
            console.print("[5b/8] Deliberacao entre Middle Managers...")
            log.info("Step 5b/8: Middle management deliberation round")
            middle = self._run_deliberation(mm_consolidator, middle, evaluations, documents)
            deliberation_executed = True

        # Step 6: Follow-up round (F)
        follow_up_executed = False
        if self.enable_follow_up_round and middle.critical_questions:
            console.print(f"[6/8] Segunda rodada: {len(middle.critical_questions)} questoes criticas...")
            log.info("Step 6/8: Follow-up round with %d questions", len(middle.critical_questions))
            evaluations = self._run_follow_up(
                agent_engine=agent_engine,
                agents=assistants,
                documents=documents,
                original_evaluations=evaluations,
                questions=middle.critical_questions,
            )
            follow_up_executed = True

            # Re-consolidate with enriched evaluations
            console.print("   Reconsolidando Middle Management com dados enriquecidos...")
            middle = mm_consolidator.run_with_documents(
                assistant_evaluations=evaluations,
                job_description_text=documents.job_description_text,
                cv_candidate_text=documents.cv_candidate_text,
                cv_client_text=documents.cv_client_text,
                interview_transcript_text=documents.interview_transcript_text,
            )
        else:
            console.print("[6/8] Sem questoes criticas pendentes.")

        # Step 7: CTO
        console.print("[7/8] Avaliacao C-Level...")
        log.info("Step 7/8: CTO final evaluation")
        cto = CTOFinalizer(llm_service=self.llm_service).run(
            job_description_text=documents.job_description_text,
            cv_candidate_text=documents.cv_candidate_text,
            cv_client_text=documents.cv_client_text,
            interview_transcript_text=documents.interview_transcript_text,
            middle_management_evaluation=middle,
            assistant_evaluations=evaluations,
        )

        # Step 8: Report
        report_candidato_name = candidato_display or candidato
        report_path: Optional[str] = None
        if generate_report:
            console.print("[8/8] Gerando relatorio final...")
            log.info("Step 8/8: Generating PDF report")
            report_path = self.report_generator.generate_report(
                vaga=vaga,
                candidato=report_candidato_name,
                assistant_evaluations=evaluations,
                middle_management_evaluation=middle,
                cto_evaluation=cto,
            )
        else:
            console.print("[8/8] Relatorio individual nao solicitado.")

        log.info("Pipeline complete for candidate=%s, report=%s", candidato, report_path)
        return PipelineOrchestrator.PipelineRunDetails(
            vaga=vaga,
            candidato=candidato,
            assistant_evaluations=evaluations,
            middle_management_evaluation=middle,
            cto_evaluation=cto,
            report_path=report_path,
            agents_selected=agents_selected,
            agents_total=agents_total,
            follow_up_round_executed=follow_up_executed,
            deliberation_executed=deliberation_executed,
        )

    def _run_follow_up(
        self,
        *,
        agent_engine: AgentEngine,
        agents: list[AgentDefinition],
        documents: DocumentSet,
        original_evaluations: list[AgentEvaluation],
        questions: list[str],
    ) -> list[AgentEvaluation]:
        """Run a second pass with follow-up questions on agents that had lower confidence."""
        follow_up_prompt_path = Path("prompts/assistants/follow_up_round.md")
        if not follow_up_prompt_path.exists():
            log.warning("Follow-up prompt not found, skipping second round")
            return original_evaluations

        template = follow_up_prompt_path.read_text(encoding="utf-8", errors="ignore")
        questions_text = "\n".join(f"- {q}" for q in questions)

        eval_by_name = {e.agent_name: e for e in original_evaluations}
        low_confidence_agents = [a for a in agents if eval_by_name.get(a.agent_name, None) and eval_by_name[a.agent_name].confidence < 0.8]

        if not low_confidence_agents:
            low_confidence_agents = agents[:5]

        log.info("Follow-up round: %d agents targeted", len(low_confidence_agents))

        updated: dict[str, AgentEvaluation] = {}
        for agent in low_confidence_agents:
            prev_eval = eval_by_name.get(agent.agent_name)
            if not prev_eval:
                continue

            rubric = agent_engine._rubric
            prompt = (
                template
                .replace("{{agent_name}}", agent.agent_name)
                .replace("{{domain}}", agent.domain)
                .replace("{{previous_evaluation_json}}", json.dumps(prev_eval.model_dump(), ensure_ascii=False))
                .replace("{{follow_up_questions}}", questions_text)
                .replace("{{context}}", agent_engine._build_context_text(agent, documents))
                .replace("{{scoring_rubric}}", rubric)
            )

            try:
                payload = self.llm_service.generate_json(prompt=prompt, context="")
                new_eval = AgentEngine._coerce_agent_payload(payload, agent=agent)
                updated[agent.agent_name] = new_eval
                log.info(
                    "Follow-up completed: %s (score: %.2f->%.2f, confidence: %.2f->%.2f)",
                    agent.agent_name, prev_eval.score, new_eval.score,
                    prev_eval.confidence, new_eval.confidence,
                )
            except Exception:
                log.exception("Follow-up failed for %s, keeping original", agent.agent_name)

        result = []
        for ev in original_evaluations:
            result.append(updated.get(ev.agent_name, ev))
        return result

    def _run_deliberation(
        self,
        mm_consolidator: MiddleManagementConsolidator,
        first_round: MiddleManagementEvaluation,
        evaluations: list[AgentEvaluation],
        documents: DocumentSet,
    ) -> MiddleManagementEvaluation:
        """Run a second round where each manager sees the others' output for calibration."""
        delib_prompt_path = Path("prompts/middle_management/deliberation_round.md")
        if not delib_prompt_path.exists():
            log.warning("Deliberation prompt not found, skipping")
            return first_round

        template = delib_prompt_path.read_text(encoding="utf-8", errors="ignore")
        rubric = mm_consolidator._load_rubric()

        manager_roles = ["tech_manager", "product_manager", "sre_manager"]
        first_round_dump = first_round.model_dump()

        calibrated_results: list[MiddleManagementEvaluation] = []
        for i, role in enumerate(manager_roles[:len(mm_consolidator.prompt_paths)]):
            own_eval_json = json.dumps(first_round_dump, ensure_ascii=False)
            other_evals = [
                {"manager": manager_roles[j], "evaluation": first_round_dump}
                for j in range(len(mm_consolidator.prompt_paths)) if j != i
            ]
            other_json = json.dumps(other_evals, ensure_ascii=False)

            prompt = (
                template
                .replace("{{manager_role}}", role)
                .replace("{{own_evaluation_json}}", own_eval_json)
                .replace("{{other_managers_json}}", other_json)
                .replace("{{scoring_rubric}}", rubric)
            )

            try:
                payload = self.llm_service.generate_json(prompt=prompt, context="")
                calibrated = MiddleManagementConsolidator._coerce_middle_payload(payload)
                calibrated_results.append(calibrated)
                log.info("Deliberation: %s calibrated score=%.2f", role, calibrated.score_consolidated)
            except Exception:
                log.exception("Deliberation failed for %s, keeping original", role)
                calibrated_results.append(first_round)

        if not calibrated_results:
            return first_round

        from app.core.orchestration.middle_and_c_level import compute_weighted_score, detect_divergences

        scores = [r.score_consolidated for r in calibrated_results]
        confidences = [r.confidence for r in calibrated_results]
        total_conf = sum(confidences)
        consolidated_score = round(
            sum(s * c for s, c in zip(scores, confidences)) / total_conf, 2
        ) if total_conf > 0 else round(sum(scores) / len(scores), 2)

        all_conflicts: list[str] = []
        all_questions: list[str] = []
        all_analysis: list[str] = []
        for r in calibrated_results:
            all_conflicts.extend(r.conflicts)
            all_questions.extend(r.critical_questions)
            all_analysis.append(r.analysis)

        seen_c: set[str] = set()
        deduped_conflicts = [c for c in all_conflicts if c and c not in seen_c and not seen_c.add(c)]
        seen_q: set[str] = set()
        deduped_questions = [q for q in all_questions if q and q not in seen_q and not seen_q.add(q)]

        divergence_flags = detect_divergences(evaluations)

        result = MiddleManagementEvaluation(
            score_consolidated=consolidated_score,
            confidence=round(sum(confidences) / len(confidences), 2),
            conflicts=deduped_conflicts,
            critical_questions=deduped_questions,
            divergence_flags=divergence_flags,
            analysis="[Pos-deliberacao]\n\n" + "\n\n".join(a for a in all_analysis if a.strip()),
        )
        log.info(
            "Deliberation complete: score=%.2f (pre-delib: %.2f)",
            result.score_consolidated, first_round.score_consolidated,
        )
        return result

    def _load_documents(self, *, vaga: str, candidato: str, client: Optional[str]) -> DocumentSet:
        exts = [".txt", ".md", ".pdf", ".docx"]

        jd_path = self.file_locator.find_by_stem(subdir="job_description", stem_fragment=vaga, extensions=exts)
        cv_candidate_path = self.file_locator.find_by_stem(subdir="candidates", stem_fragment=candidato, extensions=exts)
        interview_path = self.file_locator.find_by_stem(subdir="interviews", stem_fragment=candidato, extensions=exts)

        cv_client_fragment = client or vaga
        cv_client_text = self._safe_load_client_text(cv_client_fragment=cv_client_fragment, extensions=exts)

        return DocumentSet(
            job_description_text=self.parsing_service.load_text(jd_path),
            cv_candidate_text=self.parsing_service.load_text(cv_candidate_path),
            cv_client_text=cv_client_text,
            interview_transcript_text=self.parsing_service.load_text(interview_path),
        )

    def _safe_load_client_text(self, *, cv_client_fragment: str, extensions: list[str]) -> str:
        try:
            cv_client_path = self.file_locator.find_by_stem(
                subdir="clients",
                stem_fragment=cv_client_fragment,
                extensions=extensions,
            )
        except (FileNotFoundError, Exception):
            log.debug("Client CV not found for fragment '%s', proceeding without it", cv_client_fragment)
            return ""
        return self.parsing_service.load_text(cv_client_path)

    @staticmethod
    def _preprocess_documents(documents: DocumentSet) -> DocumentSet:
        def clean(s: str) -> str:
            cleaned = " ".join(s.split()).strip()
            if len(cleaned) > MAX_DOCUMENT_CHARS:
                log.warning("Document truncated from %d to %d chars", len(cleaned), MAX_DOCUMENT_CHARS)
            return cleaned[:MAX_DOCUMENT_CHARS]

        return DocumentSet(
            job_description_text=clean(documents.job_description_text),
            cv_candidate_text=clean(documents.cv_candidate_text),
            cv_client_text=clean(documents.cv_client_text),
            interview_transcript_text=clean(documents.interview_transcript_text),
        )
