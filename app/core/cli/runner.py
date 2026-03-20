"""Execução da sessão de avaliação a partir dos argumentos da CLI."""

from __future__ import annotations

import logging
from argparse import Namespace

from app.core.cli.data_paths import (
    candidate_fragment_for_interview,
    interview_stems,
    resolve_candidates,
    resolve_client,
    resolve_vaga,
)
from app.core.cli.terminal import (
    print_candidate_block,
    print_no_pdf,
    print_ranking_saved,
    print_report_saved,
    print_session_footer,
    print_session_header,
)
from app.core.config import settings
from app.models.schemas import CTOFinalEvaluation
from app.pipeline.orchestrator import PipelineOrchestrator
from app.services.llm_service import OpenAILLMService
from app.services.report_generator import ReportGenerator

log = logging.getLogger(__name__)


# Carrega LinkedIn opcional; retorna None se não houver arquivo.
def _read_linkedin_paste(linkedin_file: object | None) -> str | None:
    if linkedin_file is None:
        return None
    lf = linkedin_file
    if not hasattr(lf, "is_file") or not lf.is_file():
        log.error("Arquivo LinkedIn nao encontrado: %s", lf)
        raise SystemExit(1)
    return lf.read_text(encoding="utf-8", errors="replace")


# Monta orquestrador e LLM conforme flags.
def _build_orchestrator(args: Namespace) -> tuple[PipelineOrchestrator, ReportGenerator]:
    model = args.model
    report_generator = ReportGenerator()
    orchestrator = PipelineOrchestrator(
        llm_service=OpenAILLMService(force_model=model) if model else OpenAILLMService(),
        report_generator=report_generator,
        enable_agent_selection=not args.no_agent_selection,
        enable_follow_up_round=not args.no_follow_up,
        enable_deliberation=not args.no_deliberation,
    )
    return orchestrator, report_generator


# Ponto único de entrada da lógica CLI (chamado por `app.main`).
def run_cli_session(args: Namespace) -> int:
    log.debug(
        "CLI model=%s assistants=%s cto=%s",
        args.model or "(env)",
        settings.MODEL_ASSISTANTS,
        settings.MODEL_CTO,
    )

    linkedin_paste = _read_linkedin_paste(getattr(args, "linkedin_file", None))
    ni = args.non_interactive

    vaga = resolve_vaga(args.vaga, non_interactive=ni)
    candidatos = resolve_candidates(args.candidato, non_interactive=ni)
    client = resolve_client(args.client)

    stems = interview_stems(non_interactive=ni)
    candidate_runs: list[tuple[str, str]] = []
    for candidato in candidatos:
        fragment = candidate_fragment_for_interview(candidato, stems)
        candidate_runs.append((candidato, fragment))

    print_session_header(vaga=vaga, num_candidates=len(candidatos))

    orchestrator, report_generator = _build_orchestrator(args)

    log.debug("Evaluating %d candidate(s) for position '%s'", len(candidatos), vaga)
    ranking_rows: list[tuple[str, CTOFinalEvaluation]] = []

    for candidato_display, candidato_fragment in candidate_runs:
        print_candidate_block(candidato_display)
        log.debug("Processing candidate: %s", candidato_display)
        details = orchestrator.run_with_details(
            vaga=vaga,
            candidato=candidato_fragment,
            candidato_display=candidato_display,
            client=client,
            generate_report=True,
            linkedin_url=args.linkedin_url,
            linkedin_paste=linkedin_paste,
            save_history=not args.no_save_history,
        )
        if details.report_path:
            print_report_saved(details.report_path)
        else:
            print_no_pdf()
        ranking_rows.append((candidato_display, details.cto_evaluation))

    if len(ranking_rows) > 1:
        ranking_report = report_generator.generate_ranking_report(vaga=vaga, rankings=ranking_rows)
        print_ranking_saved(ranking_report)

    print_session_footer()
    log.debug("All evaluations complete")
    return 0
