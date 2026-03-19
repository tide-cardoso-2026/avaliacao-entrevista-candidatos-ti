from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from app.core.protocols import LLMService
from app.models.schemas import AgentContext, AgentDefinition, AgentEvaluation, DocumentSet

log = logging.getLogger(__name__)


class AgentEngine:
    """Layer 1: specialist assistant agents executed in parallel."""

    def __init__(
        self,
        *,
        llm_service: LLMService,
        prompts_root: str | Path = "prompts",
        max_workers: int = 5,
    ) -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)
        self.max_workers = max_workers

    def run_assistants(
        self,
        *,
        agents: list[AgentDefinition],
        documents: DocumentSet,
        on_agent_completed: Callable[[str, AgentEvaluation], None] | None = None,
    ) -> list[AgentEvaluation]:
        results: list[AgentEvaluation] = []

        def _run_single(agent: AgentDefinition) -> tuple[AgentDefinition, AgentEvaluation]:
            prompt_template = self._load_prompt(agent.prompt_path)
            prompt = (
                prompt_template.replace("{{domain}}", agent.domain)
                .replace("{{agent_name}}", agent.agent_name)
                .replace("{{context}}", self._build_context_text(agent, documents))
            )
            payload = self.llm_service.generate_json(prompt=prompt, context="")
            return agent, self._coerce_agent_payload(payload, agent=agent)

        log.info("Running %d assistants (max_workers=%d)", len(agents), self.max_workers)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_run_single, agent): agent for agent in agents}
            for future in as_completed(futures):
                agent = futures[future]
                try:
                    _, evaluation = future.result()
                    results.append(evaluation)
                    if on_agent_completed is not None:
                        on_agent_completed(agent.agent_name, evaluation)
                    log.info("Agent completed: %s (score=%.2f)", agent.agent_name, evaluation.score)
                except Exception:
                    log.exception("Agent failed: %s", agent.agent_name)
                    raise

        return results

    @staticmethod
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
    def _coerce_agent_payload(payload: dict, *, agent: AgentDefinition) -> AgentEvaluation:
        if "agent_name" in payload and "domain" in payload:
            payload = dict(payload)
            payload["strengths"] = AgentEngine._coerce_str_list(payload.get("strengths"))
            payload["improvements"] = AgentEngine._coerce_str_list(payload.get("improvements"))
            payload["risks"] = AgentEngine._coerce_str_list(payload.get("risks"))
            return AgentEvaluation(**payload)

        if "agent" in payload and "score" in payload:
            recommendation = payload.get("summary") or payload.get("recommendation") or ""
            improvements = payload.get("weaknesses") or payload.get("improvements") or []
            return AgentEvaluation(
                agent_name=agent.agent_name,
                domain=agent.domain,
                score=float(payload["score"]),
                strengths=AgentEngine._coerce_str_list(payload.get("strengths")),
                improvements=AgentEngine._coerce_str_list(improvements),
                risks=AgentEngine._coerce_str_list(payload.get("risks")),
                recommendation=str(recommendation),
            )

        raise ValueError(f"Unexpected assistant payload format: keys={sorted(payload.keys())}")

    def _load_prompt(self, prompt_path: str | Path) -> str:
        p = Path(prompt_path)
        if not p.exists():
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
