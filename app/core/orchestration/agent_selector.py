"""Seleção dinâmica de assistentes com base na descrição da vaga (uma chamada LLM meta)."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.protocols import LLMService
from app.models.schemas import AgentDefinition

log = logging.getLogger(__name__)


# Reduz o conjunto de assistentes enviados ao pipeline conforme relevância para a vaga.
class AgentSelector:

    # Aponta para `prompts/meta/agent_selector.md` e guarda referência ao LLM.
    def __init__(self, *, llm_service: LLMService, prompts_root: str | Path = "prompts") -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)
        self.prompt_path = self.prompts_root / "meta" / "agent_selector.md"

    # Chama o modelo com a lista de agentes; filtra por nome ou devolve todos se falhar/ inválido.
    def select(
        self,
        *,
        job_description_text: str,
        all_agents: list[AgentDefinition],
    ) -> list[AgentDefinition]:
        if not self.prompt_path.exists():
            return all_agents

        template = self.prompt_path.read_text(encoding="utf-8", errors="ignore")
        agents_list = "\n".join(
            f"- {a.agent_name}: {a.domain}" for a in all_agents
        )
        prompt = (
            template
            .replace("{{job_description_text}}", job_description_text)
            .replace("{{agents_list}}", agents_list)
        )

        try:
            payload = self.llm_service.generate_json(prompt=prompt, context="", layer="meta")
        except Exception:
            log.exception("Agent selection failed, falling back to all agents")
            return all_agents

        selected_names = payload.get("selected_agents", [])
        if not isinstance(selected_names, list) or not selected_names:
            log.warning("Agent selector returned empty/invalid selection, using all agents")
            return all_agents

        selected_set = {name.strip().lower() for name in selected_names if isinstance(name, str)}
        filtered = [a for a in all_agents if a.agent_name.lower() in selected_set]

        if len(filtered) < 3:
            log.warning(
                "Agent selector returned only %d agents (minimum 3 expected), using all agents",
                len(filtered),
            )
            return all_agents

        excluded = [a.agent_name for a in all_agents if a.agent_name.lower() not in selected_set]
        log.debug(
            "Agent selection: %d/%d agents selected. Excluded: %s",
            len(filtered), len(all_agents), excluded or "(none)",
        )

        rationale = payload.get("rationale", {})
        if rationale:
            for name, reason in rationale.items():
                log.debug("  Selected %s: %s", name, reason)

        return filtered
