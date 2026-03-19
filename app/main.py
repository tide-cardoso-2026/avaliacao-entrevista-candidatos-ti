from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.core.config import settings, setup_logging
from app.models.schemas import CTOFinalEvaluation
from app.pipeline.orchestrator import PipelineOrchestrator
from app.services.llm_service import OpenAILLMService
from app.services.report_generator import ReportGenerator

log = logging.getLogger(__name__)

VALID_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sistema de Avaliacao Inteligente de Candidatos.")
    parser.add_argument("--vaga", required=False, default=None, help="Nome/stem da vaga")
    parser.add_argument("--candidato", required=False, default=None, help="Nome/stem do candidato")
    parser.add_argument("--client", required=False, default=None, help="Opcional: identificar o cliente/responsavel")
    parser.add_argument(
        "--model",
        required=False,
        default=None,
        help=f"Modelo LLM (default: {settings.DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--log-level",
        required=False,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override log level",
    )
    return parser.parse_args(argv)


def _list_data_files(subdir: str) -> list[Path]:
    base = Path("data") / subdir
    if not base.exists():
        base.mkdir(parents=True, exist_ok=True)
    files = [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS]
    return sorted(files, key=lambda p: p.name.lower())


def _wait_for_files(subdir: str) -> list[Path]:
    while True:
        files = _list_data_files(subdir)
        if files:
            return files

        print(f"A pasta data/{subdir} esta vazia.")
        ans = input("Deseja adicionar arquivo(s) e tentar novamente? [Y/N]: ").strip().upper()
        if ans == "N":
            raise SystemExit(1)
        if ans != "Y":
            print("Resposta invalida. Digite Y ou N.")


def _resolve_vaga(arg_vaga: str | None) -> str:
    if arg_vaga and arg_vaga.strip():
        return arg_vaga.strip()

    job_files = _wait_for_files("job_description")
    if len(job_files) != 1:
        names = ", ".join(p.name for p in job_files)
        raise RuntimeError(
            "Para execucao sem --vaga, deve haver exatamente 1 arquivo em data/job_description. "
            f"Encontrados: {len(job_files)} ({names})"
        )
    return job_files[0].stem


def _resolve_candidates(arg_candidato: str | None) -> list[str]:
    if arg_candidato and arg_candidato.strip():
        return [arg_candidato.strip()]
    return [p.stem for p in _wait_for_files("candidates")]


def _resolve_client(arg_client: str | None) -> str | None:
    if arg_client and arg_client.strip():
        return arg_client.strip()

    client_files = _list_data_files("clients")
    if not client_files:
        return None
    if len(client_files) > 1:
        names = ", ".join(p.name for p in client_files)
        raise RuntimeError(
            "Esperado no maximo 1 arquivo em data/clients para inferencia automatica. "
            f"Encontrados: {len(client_files)} ({names})"
        )
    return client_files[0].stem


def _candidate_fragment_for_interview(candidate_stem: str, interview_stems: list[str]) -> str:
    c = candidate_stem.lower()
    for iv in interview_stems:
        if c in iv.lower():
            return candidate_stem

    tokens = [t for t in candidate_stem.replace("_", " ").replace("-", " ").split() if len(t) >= 3]
    for token in sorted(tokens, key=len, reverse=True):
        tl = token.lower()
        for iv in interview_stems:
            if tl in iv.lower():
                return token
    return candidate_stem


def main(argv: list[str]) -> int:
    load_dotenv()

    args = parse_args(argv)

    if args.log_level:
        logging.getLogger().setLevel(getattr(logging, args.log_level))

    model = args.model or settings.DEFAULT_MODEL
    log.info("Starting EntrevistaTaking (model=%s)", model)

    report_generator = ReportGenerator()
    orchestrator = PipelineOrchestrator(
        llm_service=OpenAILLMService(model=model),
        report_generator=report_generator,
    )

    vaga = _resolve_vaga(args.vaga)
    candidatos = _resolve_candidates(args.candidato)
    client = _resolve_client(args.client)

    log.info("Evaluating %d candidate(s) for position '%s'", len(candidatos), vaga)
    print(f"Iniciando avaliacao de {len(candidatos)} candidato(s) para a vaga '{vaga}'.")
    interview_stems = [p.stem for p in _wait_for_files("interviews")]
    candidate_runs: list[tuple[str, str]] = []
    for candidato in candidatos:
        fragment = _candidate_fragment_for_interview(candidato, interview_stems)
        candidate_runs.append((candidato, fragment))

    ranking_rows: list[tuple[str, CTOFinalEvaluation]] = []
    for candidato_display, candidato_fragment in candidate_runs:
        print(f"\n=== Avaliando candidato: {candidato_display} ===")
        log.info("Processing candidate: %s", candidato_display)
        details = orchestrator.run_with_details(
            vaga=vaga,
            candidato=candidato_fragment,
            candidato_display=candidato_display,
            client=client,
            generate_report=True,
        )
        print(f"Relatorio individual gerado: {details.report_path}")
        ranking_rows.append((candidato_display, details.cto_evaluation))

    if len(ranking_rows) > 1:
        ranking_report = report_generator.generate_ranking_report(vaga=vaga, rankings=ranking_rows)
        print(f"\nRelatorio de ranking consolidado gerado: {ranking_report}")

    log.info("All evaluations complete")
    return 0


def cli() -> None:
    """Entry point for the `entrevistataking` command."""
    setup_logging()
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
