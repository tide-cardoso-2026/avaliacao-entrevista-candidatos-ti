"""Camada 1: carrega prompts de assistentes, injeta contexto e paraleliza chamadas ao LLM."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.core.config import settings
from app.core.protocols import LLMService
from app.core.technical_kb_loader import read_technical_kb_file
from app.models.schemas import AgentContext, AgentDefinition, AgentEvaluation, DocumentSet, MiddleRiskItem

log = logging.getLogger(__name__)

RUBRIC_PATH = Path("prompts/shared/scoring_rubric.md")
FEW_SHOT_PATH = Path("prompts/shared/few_shot_assistant.md")
SYSTEM_LAYER_PATH = Path("prompts/shared/assistant_system_layer.md")

# Substitui {{context}} legado no template; dados reais vao em [CONTEXT] via `generate_json(..., context=...)`.
_CONTEXT_PLACEHOLDER = (
    "(O conteudo completo — vaga, CV, transcricao, materiais — esta na secao [CONTEXT] desta mensagem.)"
)
# Publico (ex.: follow-up no orchestrator).
CONTEXT_PLACEHOLDER = _CONTEXT_PLACEHOLDER


# Executa assistentes especialistas em paralelo e converte respostas JSON em `AgentEvaluation`.
class AgentEngine:

    # Carrega rubrica e few-shot compartilhados a partir de `prompts_root`.
    def __init__(
        self,
        *,
        llm_service: LLMService,
        prompts_root: str | Path = "prompts",
        max_workers: int | None = None,
        technical_questions_dir: Path | None = None,
    ) -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)
        self.max_workers = max_workers if max_workers is not None else settings.AGENT_ENGINE_MAX_WORKERS
        self._technical_questions_dir = technical_questions_dir or settings.TECHNICAL_QUESTIONS_DIR
        self._rubric = self._load_rubric()
        self._few_shot = self._load_few_shot()
        self._assistant_system_layer = self._load_assistant_system_layer()

    @property
    def assistant_system_preamble(self) -> str:
        return self._assistant_system_layer

    # Para cada agente: monta prompt, chama LLM na camada `assistants`, retorna lista de avaliações.
    def run_assistants(
        self,
        *,
        agents: list[AgentDefinition],
        documents: DocumentSet,
        on_agent_completed: Callable[[str, AgentEvaluation], None] | None = None,
    ) -> list[AgentEvaluation]:
        results: list[AgentEvaluation] = []

        # Executa um único assistente (usado dentro do ThreadPoolExecutor).
        def _run_single(agent: AgentDefinition) -> tuple[AgentDefinition, AgentEvaluation]:
            prompt_template = self._load_prompt(agent.prompt_path)
            prompt = (
                prompt_template.replace("{{domain}}", agent.domain)
                .replace("{{agent_name}}", agent.agent_name)
                .replace("{{context}}", _CONTEXT_PLACEHOLDER)
                .replace("{{scoring_rubric}}", self._rubric)
                .replace("{{few_shot_examples}}", self._few_shot)
            )
            if "{{scoring_rubric}}" not in prompt_template:
                prompt = self._rubric + "\n\n" + prompt
            if "{{few_shot_examples}}" not in prompt_template and self._few_shot:
                prompt = self._few_shot + "\n\n" + prompt
            ctx_text = self._build_context_text(agent, documents)
            payload = self.llm_service.generate_json(
                prompt=prompt,
                context=ctx_text,
                layer="assistants",
                assistant_model_tier=agent.assistant_model_tier,
                system_preamble=self._assistant_system_layer or None,
            )
            return agent, self._coerce_agent_payload(payload, agent=agent)

        log.debug("Running %d assistants (max_workers=%d)", len(agents), self.max_workers)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_run_single, agent): agent for agent in agents}
            for future in as_completed(futures):
                agent = futures[future]
                try:
                    _, evaluation = future.result()
                    results.append(evaluation)
                    if on_agent_completed is not None:
                        on_agent_completed(agent.agent_name, evaluation)
                    log.debug(
                        "Agent completed: %s (score=%.2f, confidence=%.2f, weighted=%.2f)",
                        agent.agent_name, evaluation.score, evaluation.confidence, evaluation.weighted_score,
                    )
                except Exception:
                    log.exception("Agent failed: %s", agent.agent_name)
                    raise

        return results

    # Lê `scoring_rubric.md` para calibrar notas dos assistentes.
    def _load_rubric(self) -> str:
        rubric_path = self.prompts_root / "shared" / "scoring_rubric.md"
        if rubric_path.exists():
            return rubric_path.read_text(encoding="utf-8", errors="ignore")
        if RUBRIC_PATH.exists():
            return RUBRIC_PATH.read_text(encoding="utf-8", errors="ignore")
        return ""

    # Carrega exemplos few-shot opcionais para prefixar prompts.
    def _load_few_shot(self) -> str:
        p = self.prompts_root / "shared" / "few_shot_assistant.md"
        if p.exists():
            return p.read_text(encoding="utf-8", errors="ignore")
        if FEW_SHOT_PATH.exists():
            return FEW_SHOT_PATH.read_text(encoding="utf-8", errors="ignore")
        return ""

    def _load_assistant_system_layer(self) -> str:
        p = self.prompts_root / "shared" / "assistant_system_layer.md"
        if p.exists():
            return p.read_text(encoding="utf-8", errors="ignore").strip()
        if SYSTEM_LAYER_PATH.exists():
            return SYSTEM_LAYER_PATH.read_text(encoding="utf-8", errors="ignore").strip()
        return ""

    @staticmethod
    # Normaliza o campo de lista vindo do JSON do modelo (string, lista ou dicts aninhados).
    def _coerce_str_list(items: object) -> list[str]:
        if items is None:
            return []
        if isinstance(items, str):
            return [items]
        if not isinstance(items, list):
            return [str(items)]

        out: list[str] = []
        for it in items:
            if it is None:
                continue
            if isinstance(it, str):
                v = it.strip()
                if v:
                    out.append(v)
                continue
            if isinstance(it, dict):
                for key in ("category", "text", "note", "value", "item"):
                    if key in it and it[key] is not None:
                        sv = str(it[key]).strip()
                        if sv:
                            out.append(sv)
                            break
                else:
                    out.append(str(it))
                continue
            out.append(str(it))

        return out

    @staticmethod
    def _parse_risks_for_agent(raw: object) -> tuple[list[str], list[MiddleRiskItem]]:
        """Aceita lista de strings ou objetos {description, severity}; devolve flat + estruturado."""
        if raw is None:
            return [], []
        if not isinstance(raw, list):
            return [], []
        flat: list[str] = []
        structured: list[MiddleRiskItem] = []
        for it in raw:
            if isinstance(it, dict) and ("description" in it or "severity" in it):
                structured.append(MiddleRiskItem.model_validate(it))
            elif isinstance(it, str) and it.strip():
                flat.append(it.strip())
        if structured and not flat:
            flat = [r.description for r in structured if r.description]
        return flat, structured

    @staticmethod
    # Extrai confiança do payload e limita ao intervalo [0, 1].
    def _safe_confidence(payload: dict) -> float:
        raw = payload.get("confidence")
        if raw is None:
            return 1.0
        try:
            c = float(raw)
            return max(0.0, min(1.0, c))
        except (ValueError, TypeError):
            return 1.0

    @staticmethod
    # Converte dict do LLM (formato novo ou legado com `agent`/`score`) em `AgentEvaluation`.
    def _coerce_agent_payload(payload: dict, *, agent: AgentDefinition) -> AgentEvaluation:
        confidence = AgentEngine._safe_confidence(payload)

        if "agent_name" in payload and "domain" in payload:
            payload = dict(payload)
            payload["strengths"] = AgentEngine._coerce_str_list(payload.get("strengths"))
            imps = payload.get("improvements") or payload.get("weaknesses") or []
            payload["improvements"] = AgentEngine._coerce_str_list(imps)
            raw_risks = payload.get("risks")
            flat_r, struct_r = AgentEngine._parse_risks_for_agent(raw_risks)
            if struct_r:
                payload["structured_risks"] = struct_r
                payload["risks"] = flat_r or [r.description for r in struct_r if r.description]
            else:
                payload["risks"] = AgentEngine._coerce_str_list(raw_risks)
                payload["structured_risks"] = []
            payload["missing_evidence"] = AgentEngine._coerce_str_list(
                payload.get("missing_evidence") or payload.get("missingEvidence") or []
            )
            payload.pop("weaknesses", None)
            payload.pop("missingEvidence", None)
            payload["confidence"] = confidence
            payload.pop("weighted_score", None)
            return AgentEvaluation(**payload)

        if "agent" in payload and "score" in payload:
            recommendation = payload.get("summary") or payload.get("recommendation") or ""
            improvements = payload.get("weaknesses") or payload.get("improvements") or []
            missing = payload.get("missing_evidence") or payload.get("missingEvidence") or []
            flat_r, struct_r = AgentEngine._parse_risks_for_agent(payload.get("risks"))
            risks_flat = flat_r or AgentEngine._coerce_str_list(payload.get("risks"))
            return AgentEvaluation(
                agent_name=agent.agent_name,
                domain=agent.domain,
                score=float(payload["score"]),
                confidence=confidence,
                strengths=AgentEngine._coerce_str_list(payload.get("strengths")),
                improvements=AgentEngine._coerce_str_list(improvements),
                risks=risks_flat,
                structured_risks=struct_r,
                missing_evidence=AgentEngine._coerce_str_list(missing),
                recommendation=str(recommendation),
            )

        raise ValueError(f"Unexpected assistant payload format: keys={sorted(payload.keys())}")

    # Resolve caminho absoluto ou relativo a `prompts_root` e lê o template.
    def _load_prompt(self, prompt_path: str | Path) -> str:
        p = Path(prompt_path)
        if not p.exists():
            p = self.prompts_root / str(prompt_path).lstrip("/\\")
        return p.read_text(encoding="utf-8", errors="ignore")

    # Filtra campos permitidos do `DocumentSet`, serializa e anexa KB técnica quando configurada.
    def _build_context_text(self, agent: AgentDefinition, documents: DocumentSet) -> str:
        ctx = AgentContext(
            job_description_text=documents.job_description_text if "job_description_text" in agent.allowed_context_fields else None,
            cv_candidate_text=documents.cv_candidate_text if "cv_candidate_text" in agent.allowed_context_fields else None,
            cv_client_text=documents.cv_client_text if "cv_client_text" in agent.allowed_context_fields else None,
            interview_transcript_text=documents.interview_transcript_text
            if "interview_transcript_text" in agent.allowed_context_fields
            else None,
        )
        base = ctx.to_prompt_context()
        kb = read_technical_kb_file(
            base_dir=self._technical_questions_dir,
            filename=agent.technical_kb_file,
            max_chars=settings.TECHNICAL_KB_MAX_CHARS,
        )
        if not kb.strip():
            return base
        header = f"### Base tecnica de referencia (data/technical-questions/{agent.technical_kb_file})\n"
        if base.strip():
            return f"{base}\n\n{header}{kb}"
        return header + kb
