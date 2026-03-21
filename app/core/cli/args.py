"""Argumentos da linha de comando (`python -m app.main`)."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import settings


# Parser da avaliação (vaga, candidato, LinkedIn, flags do pipeline).
def parse_cli_args(argv: list[str]) -> argparse.Namespace:
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
    parser.add_argument(
        "--linkedin-url",
        default=None,
        help="URL do perfil LinkedIn (requer PROXYCURL_API_KEY para buscar automaticamente)",
    )
    parser.add_argument(
        "--linkedin-file",
        type=Path,
        default=None,
        help="Arquivo .txt com texto colado do LinkedIn (enriquece o CV sem API)",
    )
    parser.add_argument(
        "--no-save-history",
        action="store_true",
        help="Nao gravar execucao no SQLite (data/history.db)",
    )
    parser.add_argument(
        "--no-agent-selection",
        action="store_true",
        help="Usar todos os agentes especialistas (desativa selecao dinamica)",
    )
    parser.add_argument(
        "--no-follow-up",
        action="store_true",
        help="Desativa segunda rodada de follow-up com perguntas criticas",
    )
    parser.add_argument(
        "--no-deliberation",
        action="store_true",
        help="Desativa deliberacao entre middle managers",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Falha imediata se pastas data/ estiverem vazias (sem prompt; adequado a CI/Docker).",
    )
    return parser.parse_args(argv)
