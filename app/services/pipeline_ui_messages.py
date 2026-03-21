"""Humanização de mensagens brutas de log (regex + LLM opcional). Textos de etapa vivem em `app.core.pipeline_events`."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.core.pipeline_events import event_from_legacy_step, format_pipeline_event

log = logging.getLogger(__name__)

_EXACT_LOG_MESSAGES: dict[str, str] = {
    "Step 1/8: Loading documents": "Lendo informações da vaga, do candidato e da entrevista...",
    "Step 2/8: Preprocessing documents": "Organizando o material para a avaliação...",
    "Step 3/8: Dynamic agent selection": "Definindo quem vai participar desta avaliação...",
    "Step 5/8: Middle management consolidation (round 1)": "Unindo o que cada área de liderança observou...",
    "Step 5b/8: Middle management deliberation round": "Alinhando visões entre os gestores...",
    "Step 7/8: CTO final evaluation": "Montando a avaliação final e a recomendação...",
    "Step 8/8: Generating executive PDF report": "Gerando o relatório em PDF para entrega...",
}

_LOG_PATTERN_HANDLERS: list[tuple[re.Pattern[str], Callable[[re.Match[str]], str]]] = [
    (
        re.compile(r"Step 4/8: Running (\d+) specialist assistants"),
        lambda m: f"Analisando o perfil com {m.group(1)} pareceres em paralelo...",
    ),
    (
        re.compile(r"Step 6/8: Follow-up round with (\d+) questions"),
        lambda m: f"Aprofundando {m.group(1)} ponto(s) que pediram mais detalhes...",
    ),
    (
        re.compile(r"Step 1/8: Loading documents \(vaga=.*, candidato=.*\)"),
        lambda _m: "Lendo informações da vaga, do candidato e da entrevista...",
    ),
]


# Compatibilidade: monta `PipelineEvent` legado e formata via core.
def ui_line(step_id: str, **ctx: Any) -> str:
    ev = event_from_legacy_step(step_id, **ctx)
    return format_pipeline_event(ev)


# Reescreve linha de log técnica; mapeamento + regex + LLM opcional.
def humanize_message(raw_message: str, *, llm: Any | None = None) -> str:
    text = raw_message.strip()
    if not text:
        return ""

    if text in _EXACT_LOG_MESSAGES:
        return _EXACT_LOG_MESSAGES[text]

    for pattern, handler in _LOG_PATTERN_HANDLERS:
        m = pattern.search(text)
        if m:
            return handler(m)

    if settings.HUMANIZE_UI_WITH_LLM and llm is not None:
        gen = getattr(llm, "generate_text", None)
        if callable(gen):
            try:
                prompt = (
                    "Reescreva a mensagem tecnica abaixo em UMA linha curta, em portugues do Brasil, "
                    "clara e profissional, para um usuario de RH/tecnologia. "
                    "Nao invente numeros nem etapas que nao aparecam.\n\n"
                    f"Mensagem: {text}\n\nLinha amigavel:"
                )
                out = gen(prompt=prompt, layer="meta", max_tokens=180)
                if out:
                    return out
            except Exception:
                log.exception("humanize_message: falha no fallback LLM")

    return text
