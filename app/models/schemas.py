from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field


class AgentEvaluation(BaseModel):
    agent_name: str
    domain: str
    score: float = Field(..., ge=0.0, le=10.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendation: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("score")
    @classmethod
    def _normalize_score(cls, v: float) -> float:
        return round(float(v), 2)

    @field_validator("confidence")
    @classmethod
    def _normalize_confidence(cls, v: float) -> float:
        return round(float(v), 2)

    @computed_field
    @property
    def weighted_score(self) -> float:
        return round(self.score * self.confidence, 2)


class DivergenceFlag(BaseModel):
    """Signals meaningful disagreement between evaluators."""
    agents_involved: list[str]
    score_spread: float
    description: str

    model_config = ConfigDict(extra="forbid")


class MiddleManagementEvaluation(BaseModel):
    score_consolidated: float = Field(..., ge=0.0, le=10.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    conflicts: list[str] = Field(default_factory=list)
    critical_questions: list[str] = Field(default_factory=list)
    divergence_flags: list[DivergenceFlag] = Field(default_factory=list)
    analysis: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("score_consolidated")
    @classmethod
    def _normalize_score(cls, v: float) -> float:
        return round(float(v), 2)


class FinalRating(str, Enum):
    Estagiario = "Estagiario"
    Junior = "Junior"
    Pleno = "Pleno"
    Senior = "Senior"
    Especialista = "Especialista"


class FinalIndication(str, Enum):
    Aprovar = "Aprovar"
    AprovarComRessalvas = "Aprovar com ressalvas"
    Reprovar = "Reprovar"


class CTOFinalEvaluation(BaseModel):
    final_rating: FinalRating
    score_final: float = Field(..., ge=0.0, le=10.0)
    final_indication: FinalIndication
    risks: list[str] = Field(default_factory=list)
    observations: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("score_final")
    @classmethod
    def _normalize_score(cls, v: float) -> float:
        return round(float(v), 2)


class DocumentSet(BaseModel):
    job_description_text: str
    cv_candidate_text: str
    cv_client_text: str
    interview_transcript_text: str

    model_config = ConfigDict(extra="forbid")


class AgentContext(BaseModel):
    job_description_text: str | None = None
    cv_candidate_text: str | None = None
    cv_client_text: str | None = None
    interview_transcript_text: str | None = None

    model_config = ConfigDict(extra="forbid")

    def to_prompt_context(self) -> str:
        parts: list[str] = []
        if self.job_description_text:
            parts.append("job_description:\n" + self.job_description_text)
        if self.cv_candidate_text:
            parts.append("cv_candidate:\n" + self.cv_candidate_text)
        if self.cv_client_text:
            parts.append("cv_client:\n" + self.cv_client_text)
        if self.interview_transcript_text:
            parts.append("interview_transcript:\n" + self.interview_transcript_text)
        return "\n\n".join(parts)


class AgentDefinition(BaseModel):
    agent_name: str
    domain: str
    prompt_path: str
    allowed_context_fields: list[Literal["job_description_text", "cv_candidate_text", "cv_client_text", "interview_transcript_text"]] = (
        Field(default_factory=list)
    )
    relevance_keywords: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
