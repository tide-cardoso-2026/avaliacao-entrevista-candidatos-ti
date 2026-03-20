"""CLI: resolução de arquivos em `data/`, saída de terminal e execução da sessão de avaliação."""

from app.core.cli.args import parse_cli_args
from app.core.cli.runner import run_cli_session

__all__ = ["parse_cli_args", "run_cli_session"]
