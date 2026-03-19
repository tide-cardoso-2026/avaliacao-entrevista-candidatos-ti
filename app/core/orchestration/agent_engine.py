from __future__ import annotations

from pathlib import Path

from app.models.schemas import AgentContext, AgentDefinition, AgentEvaluation, DocumentSet


class AgentEngine:
    """
    Executa a camada 1: assistentes especialistas.
    """

    def __init__(self, *, llm_service: object, prompts_root: str | Path = "prompts") -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)

    def run_assistants(
        self,
        *,
        agents: list[AgentDefinition],
        documents: DocumentSet,
        on_agent_completed: object | None = None,
    ) -> list[AgentEvaluation]:
        results: list[AgentEvaluation] = []
        for agent in agents:
            prompt_template = self._load_prompt(agent.prompt_path)
            prompt = (
                prompt_template.replace("{{domain}}", agent.domain)
                .replace("{{agent_name}}", agent.agent_name)
                .replace("{{context}}", self._build_context_text(agent, documents))
            )

            payload = self.llm_service.generate_json(prompt=prompt, context="")
            evaluation = self._coerce_agent_payload(payload, agent=agent)
            results.append(evaluation)
            if on_agent_completed is not None:
                on_agent_completed(agent.agent_name, evaluation)
        return results

    @staticmethod
    def _coerce_agent_payload(payload: dict, *, agent: AgentDefinition) -> AgentEvaluation:
        """
        Compatibilidade com 2 formatos de JSON:
        - Formato antigo (AgentEvaluation) usado no scaffold inicial.
        - Formato da issue #19 (agent/summary/weaknesses/confidence), que aqui mapeamos para
          AgentEvaluation (improvements/recommendation).
        """
        if "agent_name" in payload and "domain" in payload:
            return AgentEvaluation(**payload)

        # Formato issue #19
        if "agent" in payload and "score" in payload:
            recommendation = payload.get("summary") or payload.get("recommendation") or ""
            improvements = payload.get("weaknesses") or payload.get("improvements") or []
            return AgentEvaluation(
                agent_name=agent.agent_name,
                domain=agent.domain,
                score=float(payload["score"]),
                strengths=list(payload.get("strengths") or []),
                improvements=list(improvements),
                risks=list(payload.get("risks") or []),
                recommendation=str(recommendation),
            )

        raise ValueError(f"Formato de payload inesperado para assistente: chaves={sorted(payload.keys())}")

    def _load_prompt(self, prompt_path: str | Path) -> str:
        p = Path(prompt_path)
        if not p.exists():
            # Tenta resolver como relativo ao diretorio de prompts.
            p = self.prompts_root / str(prompt_path).lstrip("/\\")
        return p.read_text(encoding="utf-8", errors="ignore")

    def _build_context_text(self, agent: AgentDefinition, documents: DocumentSet) -> str:
        ctx = AgentContext(
            job_description_text=documents.job_description_text if "job_description_text" in agent.allowed_context_fields else None,
            cv_candidate_text=documents.cv_candidate_text if "cv_candidate_text" in agent.allowed_context_fields else None,
            cv_client_text=documents.cv_client_text if "cv_client_text" in agent.allowed_context_fields else None,
            interview_transcript_text=documents.interview_transcript_text
            if "interview_transcript_text" in agent.allowed_context_fields
            else None,
        )
        return ctx.to_prompt_context()

