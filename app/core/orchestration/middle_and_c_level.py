from __future__ import annotations

import json
from pathlib import Path

from app.models.schemas import (
    AgentEvaluation,
    CTOFinalEvaluation,
    MiddleManagementEvaluation,
)


class MiddleManagementConsolidator:
    def __init__(self, *, llm_service: object, prompts_root: str | Path = "prompts") -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)
        self.prompt_path = str(self.prompts_root / "middle_management" / "generic_consolidator.md")

    def run(self, *, assistant_evaluations: list[AgentEvaluation]) -> MiddleManagementEvaluation:
        template = self._load_prompt(self.prompt_path)
        assistants_json = json.dumps([e.model_dump() for e in assistant_evaluations], ensure_ascii=False)
        prompt = template.replace("{{assistants_evaluations_json}}", assistants_json)

        payload = self.llm_service.generate_json(prompt=prompt, context="")
        return MiddleManagementEvaluation(**payload)

    def _load_prompt(self, prompt_path: str | Path) -> str:
        return Path(prompt_path).read_text(encoding="utf-8", errors="ignore")


class CTOFinalizer:
    def __init__(self, *, llm_service: object, prompts_root: str | Path = "prompts") -> None:
        self.llm_service = llm_service
        self.prompts_root = Path(prompts_root)
        self.prompt_path = str(self.prompts_root / "c_level" / "generic_delivery_manager.md")

    def run(
        self,
        *,
        job_description_text: str,
        cv_candidate_text: str,
        cv_client_text: str,
        interview_transcript_text: str,
        middle_management_evaluation: MiddleManagementEvaluation,
    ) -> CTOFinalEvaluation:
        template = self._load_prompt(self.prompt_path)
        middle_json = json.dumps(middle_management_evaluation.model_dump(), ensure_ascii=False)
        prompt = (
            template.replace("{{job_description_text}}", job_description_text)
            .replace("{{cv_candidate_text}}", cv_candidate_text)
            .replace("{{cv_client_text}}", cv_client_text)
            .replace("{{interview_transcript_text}}", interview_transcript_text)
            .replace("{{middle_management_json}}", middle_json)
        )

        payload = self.llm_service.generate_json(prompt=prompt, context="")
        return CTOFinalEvaluation(**payload)

    def _load_prompt(self, prompt_path: str | Path) -> str:
        return Path(prompt_path).read_text(encoding="utf-8", errors="ignore")

