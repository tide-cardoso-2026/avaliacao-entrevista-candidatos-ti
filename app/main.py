import argparse
import sys
from dotenv import load_dotenv

from app.pipeline.orchestrator import PipelineOrchestrator
from app.services.llm_service import OpenAILLMService
from app.services.report_generator import ReportGenerator


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sistema de Avaliacao Inteligente de Candidatos (MVP).")
    parser.add_argument("--vaga", required=True, help="Nome/stem da vaga")
    parser.add_argument("--candidato", required=True, help="Nome/stem do candidato")
    parser.add_argument("--client", required=False, default=None, help="Opcional: identificar o cliente/responsavel")
    parser.add_argument("--model", required=False, default="gpt-4o-mini", help="Modelo LLM (default: gpt-4o-mini)")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    load_dotenv()

    args = parse_args(argv)

    orchestrator = PipelineOrchestrator(
        llm_service=OpenAILLMService(model=args.model),
        report_generator=ReportGenerator(),
    )
    output_path = orchestrator.run(vaga=args.vaga, candidato=args.candidato, client=args.client)
    print(f"Relatorio gerado: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

