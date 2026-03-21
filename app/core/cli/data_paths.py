"""Localização de arquivos em `data/` e correspondência candidato ↔ entrevista."""

from __future__ import annotations

from pathlib import Path

from app.core.cli.constants import (
    SUBDIR_CANDIDATES,
    SUBDIR_CLIENTS,
    SUBDIR_INTERVIEWS,
    SUBDIR_JOB,
    VALID_EXTENSIONS,
)


# Lista arquivos suportados em `data/<subdir>`, criando a pasta se não existir.
def list_data_files(subdir: str) -> list[Path]:
    base = Path("data") / subdir
    if not base.exists():
        base.mkdir(parents=True, exist_ok=True)
    files = [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS]
    return sorted(files, key=lambda p: p.name.lower())


# Aguarda até existir ao menos um arquivo em `data/<subdir>` (loop interativo se vazio).
def wait_for_files(subdir: str, *, non_interactive: bool = False) -> list[Path]:
    while True:
        files = list_data_files(subdir)
        if files:
            return files

        if non_interactive:
            print(f"Erro: pasta data/{subdir} esta vazia (--non-interactive).")
            raise SystemExit(1)

        print(f"A pasta data/{subdir} esta vazia.")
        ans = input("Deseja adicionar arquivo(s) e tentar novamente? [Y/N]: ").strip().upper()
        if ans == "N":
            raise SystemExit(1)
        if ans != "Y":
            print("Resposta invalida. Digite Y ou N.")


# Stem da vaga: `--vaga` ou exatamente um arquivo em `data/job_description`.
def resolve_vaga(arg_vaga: str | None, *, non_interactive: bool = False) -> str:
    if arg_vaga and arg_vaga.strip():
        return arg_vaga.strip()

    job_files = wait_for_files(SUBDIR_JOB, non_interactive=non_interactive)
    if len(job_files) != 1:
        names = ", ".join(p.name for p in job_files)
        raise RuntimeError(
            "Para execucao sem --vaga, deve haver exatamente 1 arquivo em data/job_description. "
            f"Encontrados: {len(job_files)} ({names})"
        )
    return job_files[0].stem


# Stems de candidatos: `--candidato` ou todos os arquivos em `data/candidates`.
def resolve_candidates(arg_candidato: str | None, *, non_interactive: bool = False) -> list[str]:
    if arg_candidato and arg_candidato.strip():
        return [arg_candidato.strip()]
    return [p.stem for p in wait_for_files(SUBDIR_CANDIDATES, non_interactive=non_interactive)]


# Stem do cliente em `data/clients` (no máximo um arquivo) ou `--client`.
def resolve_client(arg_client: str | None) -> str | None:
    if arg_client and arg_client.strip():
        return arg_client.strip()

    client_files = list_data_files(SUBDIR_CLIENTS)
    if not client_files:
        return None
    if len(client_files) > 1:
        names = ", ".join(p.name for p in client_files)
        raise RuntimeError(
            "Esperado no maximo 1 arquivo em data/clients para inferencia automatica. "
            f"Encontrados: {len(client_files)} ({names})"
        )
    return client_files[0].stem


# Fragmento do nome do candidato que melhor casa com stems de transcrições em `data/interviews`.
def candidate_fragment_for_interview(candidate_stem: str, interview_stems: list[str]) -> str:
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


def interview_stems(*, non_interactive: bool) -> list[str]:
    return [p.stem for p in wait_for_files(SUBDIR_INTERVIEWS, non_interactive=non_interactive)]
