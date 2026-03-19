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
            evaluation = AgentEvaluation(**payload)
            results.append(evaluation)
            if on_agent_completed is not None:
                on_agent_completed(agent.agent_name, evaluation)
        return results

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

