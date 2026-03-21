"""Modelos Pydantic compartilhados: avaliações de agentes, documentos e definições de assistentes."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


# Risco estruturado (especialistas e middle): descrição + severidade.
class MiddleRiskItem(BaseModel):
    description: str = ""
    severity: Literal["low", "medium", "high"] = "medium"

    model_config = ConfigDict(extra="forbid")

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, v: object) -> str:
        s = str(v or "medium").strip().lower()
        if s in ("low", "medium", "high"):
            return s
        return "medium"


# Resultado de um assistente especialista: nota, confiança, listas e texto de recomendação.
class AgentEvaluation(BaseModel):

    agent_name: str
    domain: str
    score: float = Field(..., ge=0.0, le=10.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    structured_risks: list[MiddleRiskItem] = Field(
        default_factory=list,
        description="Riscos com severidade (contrato padronizado).",
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Lacunas de evidencia no contexto (o que nao foi demonstrado).",
    )
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


# Signals meaningful disagreement between evaluators.
class DivergenceFlag(BaseModel):
    agents_involved: list[str]
    score_spread: float
    description: str

    model_config = ConfigDict(extra="forbid")


# Consolidação da camada middle: score, conflitos, perguntas de follow-up e análise textual.
class MiddleManagementEvaluation(BaseModel):

    score_consolidated: float = Field(..., ge=0.0, le=10.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    conflicts: list[str] = Field(default_factory=list)
    critical_questions: list[str] = Field(default_factory=list)
    divergence_flags: list[DivergenceFlag] = Field(default_factory=list)
    key_strengths: list[str] = Field(default_factory=list)
    key_gaps: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    structured_risks: list[MiddleRiskItem] = Field(default_factory=list)
    hire_recommendation: Literal["hire", "no_hire", "hire_with_risks"] | None = None
    final_recommendation: Literal["hire", "no_hire", "hire_with_risks"] | None = None
    calibration_notes: str | None = None
    analysis: str

    model_config = ConfigDict(extra="forbid")

    @computed_field
    @property
    def score(self) -> float:
        """Alias JSON `score` → score_consolidado (contrato middle_management_json)."""
        return self.score_consolidated

    @field_validator("score_consolidated")
    @classmethod
    def _normalize_score(cls, v: float) -> float:
        return round(float(v), 2)

    @field_validator("hire_recommendation", "final_recommendation", mode="before")
    @classmethod
    def _normalize_hire_literal(cls, v: object) -> str | None:
        if v is None or v == "":
            return None
        s = str(v).strip().lower().replace(" ", "_").replace("-", "_")
        if s in ("hire", "no_hire", "hire_with_risks"):
            return s
        if "no_hire" in s or s in ("no", "reject", "reprovar"):
            return "no_hire"
        if "risk" in s or "ressal" in s or "with_risks" in s:
            return "hire_with_risks"
        if s == "hire" or "aprovar" in s:
            return "hire"
        return None


# Faixa de senioridade inferida a partir do score final.
class FinalRating(str, Enum):

    Estagiario = "Estagiario"
    Junior = "Junior"
    Pleno = "Pleno"
    Senior = "Senior"
    Especialista = "Especialista"


# Decisão de negócio resumida (aprovar / ressalvas / reprovar).
class FinalIndication(str, Enum):

    Aprovar = "Aprovar"
    AprovarComRessalvas = "Aprovar com ressalvas"
    Reprovar = "Reprovar"


# Análise por camada (estratégica / tática / operacional) no laudo do CTO.
class CTOLayerBlock(BaseModel):

    assessment: str = ""
    evidence: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# Risco priorizável (impacto × probabilidade) na decisão final.
class CTORiskItem(BaseModel):

    description: str = ""
    impact: Literal["baixo", "medio", "alto"] = "medio"
    probability: Literal["baixa", "media", "alta"] = "media"

    model_config = ConfigDict(extra="forbid")

    @field_validator("impact", mode="before")
    @classmethod
    def _norm_impact(cls, v: object) -> str:
        s = str(v or "medio").strip().lower()
        s = s.replace("é", "e")
        mapping = {
            "baixo": "baixo",
            "medio": "medio",
            "médio": "medio",
            "alto": "alto",
            "low": "baixo",
            "medium": "medio",
            "high": "alto",
        }
        return mapping.get(s, "medio")

    @field_validator("probability", mode="before")
    @classmethod
    def _norm_probability(cls, v: object) -> str:
        s = str(v or "media").strip().lower()
        s = s.replace("é", "e")
        mapping = {
            "baixa": "baixa",
            "media": "media",
            "média": "media",
            "alta": "alta",
            "low": "baixa",
            "medium": "media",
            "high": "alta",
        }
        return mapping.get(s, "media")


# Laudo da camada C-level: rating, indicação, riscos e observações consolidadas.
class CTOFinalEvaluation(BaseModel):

    final_rating: FinalRating
    score_final: float = Field(..., ge=0.0, le=10.0)
    final_indication: FinalIndication
    strategic_analysis: CTOLayerBlock = Field(default_factory=CTOLayerBlock)
    tactical_analysis: CTOLayerBlock = Field(default_factory=CTOLayerBlock)
    operational_analysis: CTOLayerBlock = Field(default_factory=CTOLayerBlock)
    tradeoffs: list[str] = Field(default_factory=list)
    risks: list[CTORiskItem] = Field(default_factory=list)
    observations: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("score_final")
    @classmethod
    def _normalize_score(cls, v: float) -> float:
        return round(float(v), 2)


# Textos brutos carregados do disco para alimentar o pipeline (vaga, CVs, transcrição).
class DocumentSet(BaseModel):

    job_description_text: str
    cv_candidate_text: str
    cv_client_text: str
    interview_transcript_text: str

    model_config = ConfigDict(extra="forbid")


# Subconjunto de `DocumentSet` permitido por assistente, serializado para o prompt.
class AgentContext(BaseModel):

    job_description_text: str | None = None
    cv_candidate_text: str | None = None
    cv_client_text: str | None = None
    interview_transcript_text: str | None = None

    model_config = ConfigDict(extra="forbid")

    # Junta blocos nomeados (job_description, cv_candidate, …) para injeção no prompt.
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


# Tier de modelo por perfil (resolve `MODEL_ASSISTANTS_*` em `config`).
AssistantModelTier = Literal["default", "technical", "soft", "leadership", "psych"]


# Metadados de um assistente: nome, domínio, arquivo de prompt e campos de contexto permitidos.
class AgentDefinition(BaseModel):

    agent_name: str
    domain: str
    prompt_path: str
    allowed_context_fields: list[Literal["job_description_text", "cv_candidate_text", "cv_client_text", "interview_transcript_text"]] = (
        Field(default_factory=list)
    )
    relevance_keywords: list[str] = Field(default_factory=list)
    # Qual modelo usar na camada `assistants` (default = MODEL_ASSISTANTS).
    assistant_model_tier: AssistantModelTier = "default"
    # Arquivo em `TECHNICAL_QUESTIONS_DIR` (ex.: `backend.md`); None = sem KB injetada.
    technical_kb_file: str | None = None

    model_config = ConfigDict(extra="forbid")
