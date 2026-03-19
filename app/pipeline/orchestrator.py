from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console

from app.core.domain_rules.agent_registry import AgentRegistry
from app.core.orchestration.agent_engine import AgentEngine
from app.core.orchestration.middle_and_c_level import CTOFinalizer, MiddleManagementConsolidator
from app.models.schemas import DocumentSet
from app.services.parsing_service import ParsingService
from app.services.report_generator import ReportGenerator
from app.utils.file_locator import FileLocator


@dataclass
class PipelineOrchestrator:
    llm_service: object
    report_generator: ReportGenerator
    parsing_service: ParsingService = field(default_factory=ParsingService)
    file_locator: FileLocator = field(default_factory=FileLocator)

    def run(self, *, vaga: str, candidato: str, client: Optional[str] = None) -> str:
        console = Console()

        console.print("[1/6] Carregando dados...")
        documents = self._load_documents(vaga=vaga, candidato=candidato, client=client)

        console.print("[2/6] Processando inputs...")
        documents = self._preprocess_documents(documents)

        console.print("[3/6] Executando Assistentes...")
        assistants = AgentRegistry().get_assistants()
        agent_engine = AgentEngine(llm_service=self.llm_service)

        evaluations = agent_engine.run_assistants(
            agents=assistants,
            documents=documents,
            on_agent_completed=lambda agent_name, _ev: console.print(f"   - {agent_name} ✔"),
        )

        console.print("[4/6] Consolidando Middle Management...")
        middle = MiddleManagementConsolidator(llm_service=self.llm_service).run(
            assistant_evaluations=evaluations
        )

        console.print("[5/6] Avaliacao C-Level...")
        cto = CTOFinalizer(llm_service=self.llm_service).run(
            cv_client_text=documents.cv_client_text, middle_management_evaluation=middle
        )

        console.print("[6/6] Gerando relatorio final...")
        report_path = self.report_generator.generate_report(
            vaga=vaga,
            candidato=candidato,
            assistant_evaluations=evaluations,
            middle_management_evaluation=middle,
            cto_evaluation=cto,
        )
        return report_path

    def _load_documents(self, *, vaga: str, candidato: str, client: Optional[str]) -> DocumentSet:
        exts = [".txt", ".md", ".pdf"]

        jd_path = self.file_locator.find_by_stem(subdir="job_description", stem_fragment=vaga, extensions=exts)
        cv_candidate_path = self.file_locator.find_by_stem(subdir="candidates", stem_fragment=candidato, extensions=exts)
        interview_path = self.file_locator.find_by_stem(subdir="interviews", stem_fragment=candidato, extensions=exts)

        # CV do cliente/responsavel: tenta usar `client` se informado; caso contrario usa `vaga` como stem.
        cv_client_fragment = client or vaga
        cv_client_path = self.file_locator.find_by_stem(subdir="clients", stem_fragment=cv_client_fragment, extensions=exts)

        return DocumentSet(
            job_description_text=self.parsing_service.load_text(jd_path),
            cv_candidate_text=self.parsing_service.load_text(cv_candidate_path),
            cv_client_text=self.parsing_service.load_text(cv_client_path),
            interview_transcript_text=self.parsing_service.load_text(interview_path),
        )

    @staticmethod
    def _preprocess_documents(documents: DocumentSet) -> DocumentSet:
        # MVP: limpeza leve para reduzir ruído e manter prompts mais consistentes.
        def clean(s: str) -> str:
            return " ".join(s.split()).strip()

        return DocumentSet(
            job_description_text=clean(documents.job_description_text)[:20000],
            cv_candidate_text=clean(documents.cv_candidate_text)[:20000],
            cv_client_text=clean(documents.cv_client_text)[:20000],
            interview_transcript_text=clean(documents.interview_transcript_text)[:20000],
        )

