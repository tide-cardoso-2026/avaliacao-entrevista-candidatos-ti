"""Eventos estruturados do pipeline e texto amigável para quem acompanha o fluxo (sem jargão técnico)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# Tipo de passo lógico (estável para API/SSE/UI).
class PipelineEventKind(StrEnum):
    LOAD_DOCUMENTS = "load_documents"
    LINKEDIN_ENRICH = "linkedin_enrich"
    PREPROCESS = "preprocess"
    AGENT_SELECTION = "agent_selection"
    AGENT_SELECTION_COUNT = "agent_selection_count"
    ALL_ASSISTANTS = "all_assistants"
    RUN_ASSISTANTS = "run_assistants"
    RUN_ASSISTANTS_DONE = "run_assistants_done"
    MIDDLE_CONSOLIDATE = "middle_consolidate"
    DELIBERATION = "deliberation"
    FOLLOW_UP = "follow_up"
    FOLLOW_UP_RECONSOLIDATE = "follow_up_reconsolidate"
    FOLLOW_UP_SKIP = "follow_up_skip"
    CTO = "cto"
    PDF = "pdf"
    NO_PDF = "no_pdf"
    UNKNOWN = "unknown"


# Evento emitido pelo orquestrador (substitui strings soltas no progresso).
class PipelineEvent(BaseModel):
    kind: PipelineEventKind
    step: int = Field(ge=1, le=8)
    total_steps: int = 8
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    # Serialização estável para callbacks/WebSocket (JSON).
    def to_json_line(self) -> str:
        return self.model_dump_json()


# Converte evento em uma linha para terminal/UI em português (fluxo + etapa atual).
def format_pipeline_event(event: PipelineEvent) -> str:
    k = event.kind
    p = event.payload

    if k == PipelineEventKind.LOAD_DOCUMENTS:
        return "Lendo informações da vaga, do candidato e da entrevista..."
    if k == PipelineEventKind.LINKEDIN_ENRICH:
        return "Incluindo informações do perfil profissional (LinkedIn)..."
    if k == PipelineEventKind.PREPROCESS:
        return "Organizando o material para a avaliação..."
    if k == PipelineEventKind.AGENT_SELECTION:
        return "Definindo quem vai participar desta avaliação..."
    if k == PipelineEventKind.AGENT_SELECTION_COUNT:
        selected = int(p.get("selected", 0))
        total = int(p.get("total", 0))
        return f"    Equipe desta etapa: {selected} de {total} avaliadores."
    if k == PipelineEventKind.ALL_ASSISTANTS:
        return "Usando todos os avaliadores disponíveis nesta rodada."
    if k == PipelineEventKind.RUN_ASSISTANTS:
        count = int(p.get("count", 0))
        return f"Analisando o perfil com {count} pareceres em paralelo..."
    if k == PipelineEventKind.RUN_ASSISTANTS_DONE:
        n = int(p.get("n", 0))
        return f"Concluído — {n} pareceres recebidos."
    if k == PipelineEventKind.MIDDLE_CONSOLIDATE:
        return "Unindo o que cada área de liderança observou..."
    if k == PipelineEventKind.DELIBERATION:
        return "Alinhando visões entre os gestores..."
    if k == PipelineEventKind.FOLLOW_UP:
        n = int(p.get("n", 0))
        return f"Aprofundando {n} ponto(s) que pediram mais detalhes..."
    if k == PipelineEventKind.FOLLOW_UP_RECONSOLIDATE:
        return "Atualizando a visão geral após o aprofundamento..."
    if k == PipelineEventKind.FOLLOW_UP_SKIP:
        return "Nenhum aprofundamento extra necessário nesta rodada."
    if k == PipelineEventKind.CTO:
        return "Montando a avaliação final e a recomendação..."
    if k == PipelineEventKind.PDF:
        return "Gerando o relatório em PDF para entrega..."
    if k == PipelineEventKind.NO_PDF:
        return "Relatório em PDF não incluído nesta execução."
    if k == PipelineEventKind.UNKNOWN:
        return str(p.get("message", "Etapa em andamento"))

    return f"Etapa: {k.value}"


# --- Fábricas (uso no orquestrador) ---

def ev_load_documents() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.LOAD_DOCUMENTS, step=1)


def ev_linkedin_enrich() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.LINKEDIN_ENRICH, step=1)


def ev_preprocess() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.PREPROCESS, step=2)


def ev_agent_selection() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.AGENT_SELECTION, step=3)


def ev_agent_selection_count(*, selected: int, total: int) -> PipelineEvent:
    return PipelineEvent(
        kind=PipelineEventKind.AGENT_SELECTION_COUNT,
        step=3,
        payload={"selected": selected, "total": total},
    )


def ev_all_assistants() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.ALL_ASSISTANTS, step=3)


def ev_run_assistants(*, count: int) -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.RUN_ASSISTANTS, step=4, payload={"count": count})


def ev_run_assistants_done(*, n: int) -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.RUN_ASSISTANTS_DONE, step=4, payload={"n": n})


def ev_middle_consolidate() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.MIDDLE_CONSOLIDATE, step=5)


def ev_deliberation() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.DELIBERATION, step=5)


def ev_follow_up(*, n: int) -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.FOLLOW_UP, step=6, payload={"n": n})


def ev_follow_up_reconsolidate() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.FOLLOW_UP_RECONSOLIDATE, step=6)


def ev_follow_up_skip() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.FOLLOW_UP_SKIP, step=6)


def ev_cto() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.CTO, step=7)


def ev_pdf() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.PDF, step=8)


def ev_no_pdf() -> PipelineEvent:
    return PipelineEvent(kind=PipelineEventKind.NO_PDF, step=8)


# Compatibilidade com chamadas antigas `ui_line(step_id, **ctx)`.
_LEGACY_TO_FACTORY: dict[str, Any] = {
    "load_documents": lambda: ev_load_documents(),
    "linkedin_enrich": lambda: ev_linkedin_enrich(),
    "preprocess": lambda: ev_preprocess(),
    "agent_selection": lambda: ev_agent_selection(),
    "agent_selection_count": lambda selected, total: ev_agent_selection_count(selected=selected, total=total),
    "all_assistants": lambda: ev_all_assistants(),
    "run_assistants": lambda count: ev_run_assistants(count=count),
    "run_assistants_done": lambda n: ev_run_assistants_done(n=n),
    "middle_consolidate": lambda: ev_middle_consolidate(),
    "deliberation": lambda: ev_deliberation(),
    "follow_up": lambda n: ev_follow_up(n=n),
    "follow_up_reconsolidate": lambda: ev_follow_up_reconsolidate(),
    "follow_up_skip": lambda: ev_follow_up_skip(),
    "cto": lambda: ev_cto(),
    "pdf": lambda: ev_pdf(),
    "no_pdf": lambda: ev_no_pdf(),
}


def event_from_legacy_step(step_id: str, **ctx: Any) -> PipelineEvent:
    fn = _LEGACY_TO_FACTORY.get(step_id)
    if fn is None:
        return PipelineEvent(
            kind=PipelineEventKind.UNKNOWN,
            step=1,
            payload={"step_id": step_id, "message": f"Etapa: {step_id}"},
        )
    return fn(**ctx) if ctx else fn()
