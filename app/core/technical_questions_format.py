"""Formato canônico das linhas de perguntas técnicas em `data/technical-questions/*.md`.

O sistema (e futuras expansões automáticas) devem seguir este contrato para parsing e validação.

Gabarito para assistentes: o campo de resposta pode ser **simples** (uma linha = MIN implícito)
ou **em camadas**, separado por ` | ` com prefixos MIN:, STRONG:, ANTI:, BEHAV:, FOLLOWUP:.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# Uma linha válida: [STACK][NÍVEL][PERGUNTA][GABARITO]
# STACK: identificador curto (ex.: JAVA, PYTHON, .NET, COMMON). COMMON = transversal ao perfil.
# Nível fixo para alinhar com seções ## JUNIOR | ## PLENO | ## SENIOR do Markdown.
# Restrição: não use ']' dentro de PERGUNTA nem GABARITO (quebraria o parser simples).
TECHNICAL_QUESTION_LINE_RE = re.compile(
    r"^\[(?P<stack>[^\]]+)\]"
    r"\[(?P<level>JUNIOR|PLENO|SENIOR)\]"
    r"\[(?P<question>[^\]]+)\]"
    r"\[(?P<answer>[^\]]+)\]\s*$"
)

TechnicalLevel = Literal["JUNIOR", "PLENO", "SENIOR"]

# Camadas opcionais dentro do último campo (comparação para assistentes)
RUBRIC_PREFIX_RE = re.compile(
    r"^(MIN|STRONG|ANTI|BEHAV|FOLLOWUP)\s*:\s*",
    re.IGNORECASE,
)

# Converte o texto do gabarito em camadas para os assistentes.
#
# - Legado: texto sem `|` e sem prefixo MIN:/STRONG:/... → {"MIN": texto inteiro}
# - Estendido: segmentos separados por ` | `, cada um pode ser `CHAVE: texto`
def parse_rubric_layers(answer_field: str) -> dict[str, str]:
    s = answer_field.strip()
    if not s:
        return {"MIN": ""}

    has_pipe = "|" in s
    starts_with_key = RUBRIC_PREFIX_RE.match(s) is not None
    if not has_pipe and not starts_with_key:
        return {"MIN": s}

    parts = re.split(r"\s*\|\s*", s)
    out: dict[str, str] = {}
    orphan: list[str] = []

    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = RUBRIC_PREFIX_RE.match(p)
        if m:
            key = m.group(1).upper()
            rest = p[m.end() :].strip()
            out[key] = rest
        else:
            orphan.append(p)

    if orphan:
        merged = " | ".join(orphan)
        if "MIN" in out:
            out["MIN"] = f"{out['MIN']} | {merged}"
        else:
            out["MIN"] = merged

    if "MIN" not in out:
        out["MIN"] = s

    return out


# Uma linha parseada: stack, nível, pergunta, texto bruto do gabarito e camadas MIN/STRONG/....
@dataclass(frozen=True)
class TechnicalQuestionLine:

    stack: str
    level: TechnicalLevel
    question: str
    expected_answer: str
    rubric: dict[str, str]

    # Retorna o critério mínimo (MIN) ou o texto bruto legado.
    def min_criterion(self) -> str:
        return self.rubric.get("MIN", self.expected_answer)


# Interpreta uma linha no formato canônico; retorna None se não for uma entrada de pergunta.
def parse_technical_question_line(line: str) -> TechnicalQuestionLine | None:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None
    m = TECHNICAL_QUESTION_LINE_RE.match(raw)
    if not m:
        return None
    level = m.group("level")
    if level not in ("JUNIOR", "PLENO", "SENIOR"):
        return None
    answer_raw = m.group("answer").strip()
    rubric = parse_rubric_layers(answer_raw)
    return TechnicalQuestionLine(
        stack=m.group("stack").strip(),
        level=level,  # type: ignore[arg-type]
        question=m.group("question").strip(),
        expected_answer=answer_raw,
        rubric=rubric,
    )


# Texto linear para injeção em prompt de assistente (ordem fixa).
def rubric_as_prompt_block(rubric: dict[str, str]) -> str:
    order = ("MIN", "STRONG", "ANTI", "BEHAV", "FOLLOWUP")
    lines: list[str] = []
    for k in order:
        if k in rubric and rubric[k]:
            lines.append(f"- {k}: {rubric[k]}")
    for k in sorted(rubric.keys()):
        if k not in order and rubric.get(k):
            lines.append(f"- {k}: {rubric[k]}")
    return "\n".join(lines) if lines else ""
