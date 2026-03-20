"""CLI do EntrevistaTaking: ponto de entrada (`entrevistataking` / `python -m app.main`)."""

from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv

from app.core.cli import parse_cli_args, run_cli_session
from app.core.config import setup_logging


def main(argv: list[str]) -> int:
    load_dotenv()
    args = parse_cli_args(argv)
    if args.log_level:
        logging.getLogger().setLevel(getattr(logging, args.log_level))
    return run_cli_session(args)


def cli() -> None:
    setup_logging()
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
