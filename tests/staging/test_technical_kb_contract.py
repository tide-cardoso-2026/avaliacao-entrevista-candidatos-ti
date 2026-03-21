"""Contrato do formato de linhas em data/technical-questions/*.md (pré-core)."""

from pathlib import Path

import pytest

from app.core.technical_questions_format import (
    parse_rubric_layers,
    parse_technical_question_line,
    rubric_as_prompt_block,
    TECHNICAL_QUESTION_LINE_RE,
)

pytestmark = pytest.mark.staging

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_DIR = REPO_ROOT / "data" / "technical-questions"
# Arquivos só com prosa ou tabelas; não seguem linhas `[STACK][NÍVEL]...`.
KB_MD_EXCLUDE = frozenset({"README.md", "assistant_evaluation.md"})


def test_parse_sample_lines() -> None:
    line = "[JAVA][JUNIOR][O que é X?][Resposta]"
    p = parse_technical_question_line(line)
    assert p is not None
    assert p.stack == "JAVA"
    assert p.level == "JUNIOR"
    assert p.question == "O que é X?"
    assert p.expected_answer == "Resposta"
    assert p.rubric == {"MIN": "Resposta"}
    assert p.min_criterion() == "Resposta"


def test_layered_rubric() -> None:
    raw = (
        "MIN: conceito A | STRONG: exemplo ou trade-off | ANTI: só buzzword"
    )
    p = parse_technical_question_line(
        f"[COMMON][PLENO][Pergunta?][{raw}]"
    )
    assert p is not None
    assert p.rubric["MIN"] == "conceito A"
    assert p.rubric["STRONG"] == "exemplo ou trade-off"
    assert p.rubric["ANTI"] == "só buzzword"
    assert "MIN: conceito A" in rubric_as_prompt_block(p.rubric)


def test_parse_rubric_layers_legacy_pipe_without_keys() -> None:
    r = parse_rubric_layers("parte a | parte b")
    assert r["MIN"] == "parte a | parte b"


def test_common_stack() -> None:
    p = parse_technical_question_line(
        "[COMMON][SENIOR][Idempotência?][Chave única]"
    )
    assert p is not None
    assert p.stack == "COMMON"


def test_invalid_returns_none() -> None:
    assert parse_technical_question_line("") is None
    assert parse_technical_question_line("# título") is None
    assert parse_technical_question_line("texto solto") is None
    assert parse_technical_question_line("[A][BAD][q][a]") is None  # nível inválido


def _assert_kb_md_canonical(path: Path) -> None:
    bad: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith(">"):
            continue
        if TECHNICAL_QUESTION_LINE_RE.match(s):
            parsed = parse_technical_question_line(s)
            assert parsed is not None
            assert "MIN" in parsed.rubric and parsed.rubric["MIN"]
        else:
            bad.append(raw)
    assert not bad, (
        f"{path.name}: linhas não vazias que não são comentário devem ser formato canônico:\n"
        + "\n".join(bad[:20])
    )


@pytest.mark.skipif(not KB_DIR.is_dir(), reason="pasta technical-questions ausente")
def test_all_kb_md_lines_match_regex() -> None:
    files = sorted(p for p in KB_DIR.glob("*.md") if p.name not in KB_MD_EXCLUDE)
    assert files, "esperado ao menos um .md de perguntas em data/technical-questions"
    for path in files:
        _assert_kb_md_canonical(path)
