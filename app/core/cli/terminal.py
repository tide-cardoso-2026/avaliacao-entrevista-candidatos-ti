"""Mensagens de terminal — mesmo estilo do pipeline (`  •` / `    `), linguagem para quem acompanha o fluxo."""

from __future__ import annotations

from pathlib import Path


def print_session_header(*, vaga: str, num_candidates: int) -> None:
    print()
    print(f"  • Início da avaliação — vaga «{vaga}», {num_candidates} candidato(s).")


def print_candidate_block(candidato_display: str) -> None:
    print()
    print(f"  • Avaliando: {candidato_display}")


def print_report_saved(report_path: str) -> None:
    rp = Path(report_path)
    folder = rp.resolve().parent
    print()
    print("    Concluído — relatório em PDF pronto.")
    print(f"    {folder}")
    print(f"    {rp.name}")


def print_no_pdf() -> None:
    print()
    print("    Concluído — avaliação registrada sem PDF nesta execução.")


def print_ranking_saved(ranking_path: str) -> None:
    rr = Path(ranking_path)
    print()
    print("    Concluído — comparativo entre candidatos gerado.")
    print(f"    {rr.resolve().parent}")
    print(f"    {rr.name}")


def print_session_footer() -> None:
    print()
    print("  • Tudo certo — você pode fechar esta janela ou rodar outra avaliação.")
