"""Orquestração do fluxo completo: documentos → assistentes → middle → follow-up → CTO → PDF/histórico."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from app.core.config import settings
from app.core.domain_rules.agent_registry import AgentRegistry
from app.core.orchestration.agent_engine import CONTEXT_PLACEHOLDER, AgentEngine
from app.core.orchestration.agent_selector import AgentSelector
from app.core.orchestration.middle_and_c_level import (
    CTOFinalizer,
    MANAGER_ROLES,
    MiddleManagementConsolidator,
)
from app.core.pipeline_contract import deliberation_should_run, normalize_agent_evaluations
from app.core.pipeline_events import (
    PipelineEvent,
    ev_agent_selection,
    ev_agent_selection_count,
    ev_all_assistants,
    ev_cto,
    ev_deliberation,
    ev_follow_up,
    ev_follow_up_reconsolidate,
    ev_follow_up_skip,
    ev_linkedin_enrich,
    ev_load_documents,
    ev_middle_consolidate,
    ev_no_pdf,
    ev_pdf,
    ev_preprocess,
    ev_run_assistants,
    ev_run_assistants_done,
    format_pipeline_event,
)
from app.core.protocols import LLMService
from app.models.schemas import (
    AgentDefinition,
    AgentEvaluation,
    CTOFinalEvaluation,
    DocumentSet,
    MiddleManagementEvaluation,
)
from app.services.executive_report_service import build_executive_report
from app.services.parsing_service import ParsingService
from app.services.report_generator import ReportGenerator
from app.utils.file_locator import FileLocator

log = logging.getLogger(__name__)

MAX_DOCUMENT_CHARS = 20_000


# Fachada que carrega arquivos, executa camadas LLM e opcionalmente persiste histórico.
@dataclass
class PipelineOrchestrator:
    llm_service: LLMService
    report_generator: ReportGenerator
    parsing_service: ParsingService = field(default_factory=ParsingService)
    file_locator: FileLocator = field(default_factory=FileLocator)
    enable_agent_selection: bool = True
    enable_follow_up_round: bool = True
    enable_deliberation: bool = True

    # Resultado estruturado de uma execução (scores, flags e caminho do PDF).
    @dataclass
    class PipelineRunDetails:
        vaga: str
        candidato: str
        assistant_evaluations: list[AgentEvaluation]
        middle_management_evaluation: MiddleManagementEvaluation
        cto_evaluation: CTOFinalEvaluation
        report_path: str | None = None
        agents_selected: int = 0
        agents_total: int = 0
        follow_up_round_executed: bool = False
        deliberation_executed: bool = False
        history_run_id: int | None = None  # id em evaluation_runs (SQLite)

    # Executa o pipeline e devolve apenas o caminho do PDF gerado.
    def run(self, *, vaga: str, candidato: str, client: str | None = None, save_history: bool = True) -> str:
        result = self.run_with_details(
            vaga=vaga, candidato=candidato, client=client, generate_report=True, save_history=save_history
        )
        if not result.report_path:
            raise RuntimeError("Falha ao gerar relatorio no pipeline.")
        return result.report_path

    # Executa o pipeline com callbacks de progresso, LinkedIn opcional e retorno detalhado.
    def run_with_details(
        self,
        *,
        vaga: str,
        candidato: str,
        candidato_display: str | None = None,
        client: str | None = None,
        generate_report: bool = True,
        progress_callback: Callable[[str, str], None] | None = None,
        on_pipeline_event: Callable[[PipelineEvent], None] | None = None,
        linkedin_url: str | None = None,
        linkedin_paste: str | None = None,
        save_history: bool = True,
    ) -> PipelineRunDetails:
        console = Console()

        def emit(step: str, detail: str) -> None:
            if progress_callback:
                progress_callback(step, detail)

        def _present(ev: PipelineEvent, *, channel: str = "step") -> str:
            msg = format_pipeline_event(ev)
            console.print(f"  • {msg}")
            if on_pipeline_event:
                on_pipeline_event(ev)
            emit(channel, msg)
            return msg

        def _present_sub(ev: PipelineEvent) -> None:
            msg = format_pipeline_event(ev)
            console.print(f"    {msg}")
            if on_pipeline_event:
                on_pipeline_event(ev)

        # Step 1: Load
        _present(ev_load_documents())
        log.debug("Step 1/8: Loading documents (vaga=%s, candidato=%s)", vaga, candidato)
        documents = self._load_documents(vaga=vaga, candidato=candidato, client=client)

        if linkedin_url or linkedin_paste:
            from app.services.linkedin_service import enrich_candidate_cv

            _present(ev_linkedin_enrich(), channel="linkedin")
            documents = DocumentSet(
                job_description_text=documents.job_description_text,
                cv_candidate_text=enrich_candidate_cv(
                    documents.cv_candidate_text,
                    linkedin_url=linkedin_url,
                    linkedin_paste=linkedin_paste,
                ),
                cv_client_text=documents.cv_client_text,
                interview_transcript_text=documents.interview_transcript_text,
            )

        # Step 2: Preprocess
        _present(ev_preprocess())
        log.debug("Step 2/8: Preprocessing documents")
        documents = self._preprocess_documents(documents)

        # Step 3: Agent selection (C)
        all_assistants = AgentRegistry().get_assistants()
        agents_total = len(all_assistants)
        if self.enable_agent_selection:
            _present(ev_agent_selection())
            log.debug("Step 3/8: Dynamic agent selection")
            selector = AgentSelector(llm_service=self.llm_service)
            assistants = selector.select(
                job_description_text=documents.job_description_text,
                all_agents=all_assistants,
            )
            _present_sub(ev_agent_selection_count(selected=len(assistants), total=agents_total))
            emit("agents_selected", f"{len(assistants)}/{agents_total}")
        else:
            _present(ev_all_assistants())
            assistants = all_assistants
        agents_selected = len(assistants)

        # Step 4: Run assistants
        _present(ev_run_assistants(count=len(assistants)))
        log.debug("Step 4/8: Running %d specialist assistants", len(assistants))
        agent_engine = AgentEngine(llm_service=self.llm_service)

        def _on_agent_done(agent_name: str, _ev: AgentEvaluation) -> None:
            emit("agent_done", agent_name)

        evaluations = agent_engine.run_assistants(
            agents=assistants,
            documents=documents,
            on_agent_completed=_on_agent_done,
        )
        evaluations = normalize_agent_evaluations(evaluations)
        _present_sub(ev_run_assistants_done(n=len(evaluations)))

        # Step 5: Middle managers (paralelo) + deliberação condicional + merge / pré-CTO
        _present(ev_middle_consolidate())
        log.debug("Step 5/8: Middle management (managers parallel + consolidate)")
        mm_consolidator = MiddleManagementConsolidator(llm_service=self.llm_service)
        managers_round = mm_consolidator.run_managers_parallel(
            assistant_evaluations=evaluations,
            job_description_text=documents.job_description_text,
            cv_candidate_text=documents.cv_candidate_text,
            cv_client_text=documents.cv_client_text,
            interview_transcript_text=documents.interview_transcript_text,
        )

        deliberation_executed = False
        if (
            self.enable_deliberation
            and len(mm_consolidator.prompt_paths) > 1
            and deliberation_should_run(
                managers_round,
                score_threshold=settings.MIDDLE_DELIBERATION_SCORE_THRESHOLD,
            )
        ):
            _present(ev_deliberation())
            log.debug("Step 5b/8: Middle management deliberation (own vs peers)")
            managers_round = self._run_deliberation(mm_consolidator, managers_round, evaluations, documents)
            deliberation_executed = True

        middle = mm_consolidator.finalize_middle_managers(managers_round, evaluations)

        # Step 6: Follow-up round (F)
        follow_up_executed = False
        if self.enable_follow_up_round and middle.critical_questions:
            nq = len(middle.critical_questions)
            _present(ev_follow_up(n=nq))
            log.debug("Step 6/8: Follow-up round with %d questions", len(middle.critical_questions))
            evaluations = self._run_follow_up(
                agent_engine=agent_engine,
                agents=assistants,
                documents=documents,
                original_evaluations=evaluations,
                questions=middle.critical_questions,
            )
            follow_up_executed = True

            # Re-consolidate with enriched evaluations
            _present(ev_follow_up_reconsolidate())
            managers_after = mm_consolidator.run_managers_parallel(
                assistant_evaluations=evaluations,
                job_description_text=documents.job_description_text,
                cv_candidate_text=documents.cv_candidate_text,
                cv_client_text=documents.cv_client_text,
                interview_transcript_text=documents.interview_transcript_text,
            )
            middle = mm_consolidator.finalize_middle_managers(managers_after, evaluations)
        else:
            _present(ev_follow_up_skip())

        # Step 7: CTO
        _present(ev_cto())
        log.debug("Step 7/8: CTO final evaluation")
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
        report_path: str | None = None
        if generate_report:
            _present(ev_pdf())
            log.debug("Step 8/8: Generating executive PDF report")
            executive = build_executive_report(
                self.llm_service,
                vaga=vaga,
                candidato_display=report_candidato_name,
                assistant_evaluations=evaluations,
                middle=middle,
                cto=cto,
            )
            report_path = self.report_generator.generate_report(
                vaga=vaga,
                candidato=report_candidato_name,
                executive=executive,
            )
        else:
            _present(ev_no_pdf())

        history_run_id: int | None = None
        if save_history:
            try:
                from app.services.history_service import save_evaluation_run

                full_payload = {
                    "assistant_evaluations": [e.model_dump() for e in evaluations],
                    "middle": middle.model_dump(),
                    "cto": cto.model_dump(),
                }
                history_run_id = save_evaluation_run(
                    vaga=vaga,
                    candidato=candidato_display or candidato,
                    client_stem=client,
                    cto=cto,
                    pdf_path=report_path,
                    full_payload=full_payload,
                )
                emit("history_saved", str(history_run_id))
            except Exception:
                log.exception("Falha ao salvar historico no banco")

        log.debug("Pipeline complete for candidate=%s, report=%s", candidato, report_path)
        emit("done", report_path or "")
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
            history_run_id=history_run_id,
        )

    # Run a second pass with follow-up questions on agents that had lower confidence.
    def _run_follow_up(
        self,
        *,
        agent_engine: AgentEngine,
        agents: list[AgentDefinition],
        documents: DocumentSet,
        original_evaluations: list[AgentEvaluation],
        questions: list[str],
    ) -> list[AgentEvaluation]:
        follow_up_prompt_path = Path("prompts/assistants/follow_up_round.md")
        if not follow_up_prompt_path.exists():
            return original_evaluations

        template = follow_up_prompt_path.read_text(encoding="utf-8", errors="ignore")
        questions_text = "\n".join(f"- {q}" for q in questions)

        eval_by_name = {e.agent_name: e for e in original_evaluations}
        low_confidence_agents = [
            a for a in agents if eval_by_name.get(a.agent_name) and eval_by_name[a.agent_name].confidence < 0.8
        ]

        if not low_confidence_agents:
            low_confidence_agents = agents[:5]

        log.debug("Follow-up round: %d agents targeted", len(low_confidence_agents))

        updated: dict[str, AgentEvaluation] = {}
        for agent in low_confidence_agents:
            prev_eval = eval_by_name.get(agent.agent_name)
            if not prev_eval:
                continue

            rubric = agent_engine._rubric
            prev_score = float(prev_eval.score)
            prev_conf = float(prev_eval.confidence)
            ctx_follow = agent_engine._build_context_text(agent, documents)
            prompt = (
                template.replace("{{agent_name}}", agent.agent_name)
                .replace("{{domain}}", agent.domain)
                .replace("{{previous_evaluation_json}}", json.dumps(prev_eval.model_dump(), ensure_ascii=False))
                .replace("{{follow_up_questions}}", questions_text)
                .replace("{{context}}", CONTEXT_PLACEHOLDER)
                .replace("{{scoring_rubric}}", rubric)
                .replace("{{previous_score}}", f"{prev_score:.2f}")
                .replace("{{previous_confidence}}", f"{prev_conf:.2f}")
            )

            try:
                preamble = agent_engine.assistant_system_preamble.strip() or None
                payload = self.llm_service.generate_json(
                    prompt=prompt,
                    context=ctx_follow,
                    layer="assistants",
                    assistant_model_tier=agent.assistant_model_tier,
                    system_preamble=preamble,
                )
                new_eval = AgentEngine._coerce_agent_payload(payload, agent=agent)
                # Se o modelo copiar um template com zeros, nao descarte a avaliacao anterior.
                if prev_score > 0 and new_eval.score == 0.0 and new_eval.confidence == 0.0:
                    log.warning(
                        "Follow-up retornou score/confidence zero; mantendo valores anteriores para %s",
                        agent.agent_name,
                    )
                    new_eval = prev_eval.model_copy(
                        update={
                            "recommendation": new_eval.recommendation or prev_eval.recommendation,
                        }
                    )
                updated[agent.agent_name] = new_eval
                log.debug(
                    "Follow-up completed: %s (score: %.2f->%.2f, confidence: %.2f->%.2f)",
                    agent.agent_name,
                    prev_eval.score,
                    new_eval.score,
                    prev_eval.confidence,
                    new_eval.confidence,
                )
            except Exception:
                log.exception("Follow-up failed for %s, keeping original", agent.agent_name)

        result = []
        for ev in original_evaluations:
            result.append(updated.get(ev.agent_name, ev))
        return normalize_agent_evaluations(result)

    # Cada manager vê a própria avaliação e as dos pares; retorna lista na mesma ordem.
    def _run_deliberation(
        self,
        mm_consolidator: MiddleManagementConsolidator,
        managers: list[MiddleManagementEvaluation],
        evaluations: list[AgentEvaluation],
        documents: DocumentSet,
    ) -> list[MiddleManagementEvaluation]:
        delib_prompt_path = Path("prompts/middle_management/deliberation_round.md")
        if not delib_prompt_path.exists():
            return managers

        template = delib_prompt_path.read_text(encoding="utf-8", errors="ignore")
        rubric = mm_consolidator._load_rubric()

        n = min(len(managers), len(mm_consolidator.prompt_paths))
        manager_roles = MANAGER_ROLES[:n]
        manager_dumps = [m.model_dump() for m in managers[:n]]

        calibrated_results: list[MiddleManagementEvaluation] = []
        for i, role in enumerate(manager_roles):
            own_eval_json = json.dumps(manager_dumps[i], ensure_ascii=False)
            other_evals = [
                {"manager": manager_roles[j], "evaluation": manager_dumps[j]}
                for j in range(n)
                if j != i
            ]
            other_json = json.dumps(other_evals, ensure_ascii=False)

            prompt = (
                template.replace("{{manager_role}}", role)
                .replace("{{own_evaluation_json}}", own_eval_json)
                .replace("{{other_managers_json}}", other_json)
                .replace("{{scoring_rubric}}", rubric)
                .replace("{{middle_principles}}", mm_consolidator._middle_principles)
            )
            if "{{scoring_rubric}}" not in template:
                prompt = rubric + "\n\n" + prompt
            if "{{middle_principles}}" not in template and mm_consolidator._middle_principles:
                prompt = mm_consolidator._middle_principles + "\n\n" + prompt

            try:
                payload = self.llm_service.generate_json(prompt=prompt, context="", layer="middle")
                calibrated = MiddleManagementConsolidator._coerce_middle_payload(payload)
                calibrated_results.append(calibrated)
                log.debug("Deliberation: %s calibrated score=%.2f", role, calibrated.score_consolidated)
            except Exception:
                log.exception("Deliberation failed for %s, keeping original", role)
                calibrated_results.append(managers[i])

        tail = managers[n:] if n < len(managers) else []
        return calibrated_results + tail

    # Localiza e parseia vaga, CV do candidato, transcrição e opcionalmente CV do cliente.
    def _load_documents(self, *, vaga: str, candidato: str, client: str | None) -> DocumentSet:
        exts = [".txt", ".md", ".pdf", ".docx"]

        jd_path = self.file_locator.find_by_stem(subdir="job_description", stem_fragment=vaga, extensions=exts)
        cv_candidate_path = self.file_locator.find_by_stem(
            subdir="candidates", stem_fragment=candidato, extensions=exts
        )
        interview_path = self.file_locator.find_by_stem(subdir="interviews", stem_fragment=candidato, extensions=exts)

        cv_client_fragment = client or vaga
        cv_client_text = self._safe_load_client_text(cv_client_fragment=cv_client_fragment, extensions=exts)

        return DocumentSet(
            job_description_text=self.parsing_service.load_text(jd_path),
            cv_candidate_text=self.parsing_service.load_text(cv_candidate_path),
            cv_client_text=cv_client_text,
            interview_transcript_text=self.parsing_service.load_text(interview_path),
        )

    # Carrega texto do perfil do cliente em `data/clients` ou retorna string vazia se não houver.
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
    # Normaliza espaços e trunca textos muito longos para limitar tokens na chamada LLM.
    def _preprocess_documents(documents: DocumentSet) -> DocumentSet:
        def clean(s: str) -> str:
            cleaned = " ".join(s.split()).strip()
            if len(cleaned) > MAX_DOCUMENT_CHARS:
                log.debug("Document truncated from %d to %d chars", len(cleaned), MAX_DOCUMENT_CHARS)
            return cleaned[:MAX_DOCUMENT_CHARS]

        return DocumentSet(
            job_description_text=clean(documents.job_description_text),
            cv_candidate_text=clean(documents.cv_candidate_text),
            cv_client_text=clean(documents.cv_client_text),
            interview_transcript_text=clean(documents.interview_transcript_text),
        )
