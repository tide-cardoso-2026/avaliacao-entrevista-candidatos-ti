from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console

from app.core.domain_rules.agent_registry import AgentRegistry
from app.core.orchestration.agent_engine import AgentEngine
from app.core.orchestration.middle_and_c_level import CTOFinalizer, MiddleManagementConsolidator
from app.core.protocols import LLMService
from app.models.schemas import AgentEvaluation, CTOFinalEvaluation, DocumentSet, MiddleManagementEvaluation
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

    @dataclass
    class PipelineRunDetails:
        vaga: str
        candidato: str
        assistant_evaluations: list[AgentEvaluation]
        middle_management_evaluation: MiddleManagementEvaluation
        cto_evaluation: CTOFinalEvaluation
        report_path: Optional[str] = None

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

        console.print("[1/6] Carregando dados...")
        log.info("Step 1/6: Loading documents (vaga=%s, candidato=%s)", vaga, candidato)
        documents = self._load_documents(vaga=vaga, candidato=candidato, client=client)

        console.print("[2/6] Processando inputs...")
        log.info("Step 2/6: Preprocessing documents")
        documents = self._preprocess_documents(documents)

        console.print("[3/6] Executando Assistentes...")
        log.info("Step 3/6: Running specialist assistants")
        assistants = AgentRegistry().get_assistants()
        agent_engine = AgentEngine(llm_service=self.llm_service)

        evaluations = agent_engine.run_assistants(
            agents=assistants,
            documents=documents,
            on_agent_completed=lambda agent_name, _ev: console.print(f"   - {agent_name} [OK]"),
        )

        console.print("[4/6] Consolidando Middle Management...")
        log.info("Step 4/6: Middle management consolidation")
        middle = MiddleManagementConsolidator(llm_service=self.llm_service).run_with_documents(
            assistant_evaluations=evaluations,
            job_description_text=documents.job_description_text,
            cv_candidate_text=documents.cv_candidate_text,
            cv_client_text=documents.cv_client_text,
            interview_transcript_text=documents.interview_transcript_text,
        )

        console.print("[5/6] Avaliacao C-Level...")
        log.info("Step 5/6: CTO final evaluation")
        cto = CTOFinalizer(llm_service=self.llm_service).run(
            job_description_text=documents.job_description_text,
            cv_candidate_text=documents.cv_candidate_text,
            cv_client_text=documents.cv_client_text,
            interview_transcript_text=documents.interview_transcript_text,
            middle_management_evaluation=middle,
        )

        report_candidato_name = candidato_display or candidato
        report_path: Optional[str] = None
        if generate_report:
            console.print("[6/6] Gerando relatorio final...")
            log.info("Step 6/6: Generating PDF report")
            report_path = self.report_generator.generate_report(
                vaga=vaga,
                candidato=report_candidato_name,
                assistant_evaluations=evaluations,
                middle_management_evaluation=middle,
                cto_evaluation=cto,
            )
        else:
            console.print("[6/6] Relatorio individual nao solicitado.")

        log.info("Pipeline complete for candidate=%s, report=%s", candidato, report_path)
        return PipelineOrchestrator.PipelineRunDetails(
            vaga=vaga,
            candidato=candidato,
            assistant_evaluations=evaluations,
            middle_management_evaluation=middle,
            cto_evaluation=cto,
            report_path=report_path,
        )

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
