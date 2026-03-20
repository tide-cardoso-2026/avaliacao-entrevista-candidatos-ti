"""
Somente a camada de assistentes: Dev Backend avalia o candidato usando a base tecnica backend.md.

Nao passa pelo orchestrator, middle nem CTO. Valida integracao AgentEngine + KB + prompt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.domain_rules.agent_registry import AgentRegistry
from app.core.orchestration.agent_engine import AgentEngine
from app.core.protocols import LLMService
from app.models.schemas import AgentEvaluation, DocumentSet

from .staging_pdf import write_assistants_staging_pdf

pytestmark = pytest.mark.staging

REPO_ROOT = Path(__file__).resolve().parents[2]
STAGING_OUTPUT_DIR = REPO_ROOT / "staging" / "output"
BACKEND_KB = REPO_ROOT / "data" / "technical-questions" / "backend.md"
ASSISTANT_GUIDE = REPO_ROOT / "data" / "technical-questions" / "assistant_evaluation.md"


# LLM fake que grava o prompt e devolve JSON no formato esperado pelo AgentEngine.
class RecordingAssistantLLM:

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def generate_json(
        self,
        *,
        prompt: str,
        context: str,
        layer: str = "assistants",
        assistant_model_tier: str | None = None,
        system_preamble: str | None = None,
    ) -> dict:
        self.calls.append(
            {
                "prompt": prompt,
                "context": context,
                "layer": layer,
                "assistant_model_tier": assistant_model_tier,
                "system_preamble": system_preamble,
            }
        )
        return {
            "agent": "Dev Backend",
            "score": 8.0,
            "summary": "Candidato demonstra dominio alinhado aos criterios da base tecnica.",
            "strengths": ["Explicou idempotencia em APIs com clareza"],
            "weaknesses": ["Mensageria distribuida: resposta superficial"],
            "risks": ["Validar experiencia real com circuit breaker em producao"],
            "missing_evidence": ["Nao ha tracos de operacao de filas em escala no material"],
            "confidence": 0.85,
        }


def _dev_backend_agent():
    reg = AgentRegistry(prompts_root=REPO_ROOT / "prompts")
    for a in reg.get_assistants():
        if a.agent_name == "Dev Backend":
            return a
    raise RuntimeError("Dev Backend nao encontrado no registry")


def _documents_with_backend_kb(*, transcript: str) -> DocumentSet:
    # A KB `backend.md` e injetada pelo AgentEngine a partir de `technical_kb_file` do agente.
    guide_text = ""
    if ASSISTANT_GUIDE.is_file():
        guide_text = (
            "\n\n### Instrucoes para comparacao com o gabarito (assistant_evaluation)\n"
            + ASSISTANT_GUIDE.read_text(encoding="utf-8")
        )
    return DocumentSet(
        job_description_text="Engenheiro de Software Backend Pleno — APIs REST, Java/Spring.",
        cv_candidate_text="3 anos backend Java, REST, SQL.",
        cv_client_text="",
        interview_transcript_text=transcript + guide_text,
    )


@pytest.mark.skipif(not BACKEND_KB.is_file(), reason="backend.md ausente")
def test_dev_backend_assistant_runs_with_kb_in_context():
    llm = RecordingAssistantLLM()
    assert isinstance(llm, LLMService)

    agent = _dev_backend_agent()
    engine = AgentEngine(llm_service=llm, prompts_root=REPO_ROOT / "prompts", max_workers=1)

    transcript = (
        "Entrevistador: Como voce garante idempotencia em APIs?\n"
        "Candidato: Uso chave de idempotencia no header ou body, armazeno estado "
        "da operacao e descarto duplicatas no servidor antes de efeitos colaterais.\n"
    )
    docs = _documents_with_backend_kb(transcript=transcript)

    results = engine.run_assistants(agents=[agent], documents=docs)

    assert len(results) == 1
    ev = results[0]
    assert isinstance(ev, AgentEvaluation)
    assert ev.agent_name == "Dev Backend"
    assert ev.domain == "Backend (APIs, performance, escalabilidade)"
    assert 0.0 <= ev.score <= 10.0
    assert ev.recommendation  # vem do summary coerced
    assert isinstance(ev.missing_evidence, list)

    assert len(llm.calls) == 1
    assert llm.calls[0]["layer"] == "assistants"
    assert llm.calls[0].get("assistant_model_tier") == "technical"
    assert llm.calls[0].get("system_preamble")
    prompt = llm.calls[0]["prompt"]
    ctx = llm.calls[0]["context"]

    # Base tecnica + transcricao vao na secao [CONTEXT] (user), nao embutidos no template.
    assert "[COMMON][SENIOR][Como garantir idempotência em APIs?" in ctx or (
        "idempotência" in ctx and "[COMMON]" in ctx
    ), "Context deve incluir linhas canonicas da base backend.md"

    assert "Base tecnica de referencia" in ctx or "technical-questions" in ctx
    assert "interview_transcript:" in ctx

    pdf_path = write_assistants_staging_pdf(
        output_dir=STAGING_OUTPUT_DIR,
        evaluations=results,
        job_title="Engenheiro de Software Backend Pleno (teste staging)",
        candidate_name="Candidato Staging Backend",
        prompt_excerpt=prompt + "\n\n[CONTEXT]\n" + ctx,
        footer_note="LLM mock (RecordingAssistantLLM). Pipeline completo nao executado.",
    )
    assert pdf_path.is_file()
    assert pdf_path.stat().st_size > 0


@pytest.mark.skipif(not BACKEND_KB.is_file(), reason="backend.md ausente")
# Rubrica compartilhada continua anexada (calibracao dos assistentes).
def test_prompt_includes_scoring_rubric_shared():
    llm = RecordingAssistantLLM()
    agent = _dev_backend_agent()
    engine = AgentEngine(llm_service=llm, prompts_root=REPO_ROOT / "prompts", max_workers=1)
    docs = _documents_with_backend_kb(transcript="Candidato: resposta minima.")
    engine.run_assistants(agents=[agent], documents=docs)

    prompt = llm.calls[0]["prompt"]
    rubric_path = REPO_ROOT / "prompts" / "shared" / "scoring_rubric.md"
    if rubric_path.is_file():
        snippet = rubric_path.read_text(encoding="utf-8", errors="ignore")[:80]
        assert snippet[:40] in prompt or "score" in prompt.lower()
