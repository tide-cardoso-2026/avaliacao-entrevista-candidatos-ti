"""Relatório executivo consolidado (contrato JSON) para PDF de 1–2 páginas sem ruído técnico."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

RecommendationCode = Literal["STRONG_HIRE", "HIRE", "NO_HIRE"]
LevelCode = Literal["junior", "mid", "senior", "staff"]


# Metadados exibidos na capa.
class CandidateHeader(BaseModel):
    name: str
    role: str
    date: str

    model_config = {"extra": "forbid"}


# Decisão sintética alinhada ao scorecard ponderado.
class DecisionBlock(BaseModel):
    recommendation: RecommendationCode
    level: LevelCode
    score: float = Field(..., ge=0.0, le=10.0)
    confidence: float = Field(..., ge=0.0, le=1.0)

    model_config = {"extra": "forbid"}

    @field_validator("score", mode="before")
    @classmethod
    def _round_score(cls, v: object) -> float:
        return round(float(v), 2)

    @field_validator("confidence", mode="before")
    @classmethod
    def _round_conf(cls, v: object) -> float:
        return round(float(v), 2)


# Listas curtas para a capa executiva.
class HighlightsBlock(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


# Sub-scores por dimensão (pesos fixos na normalização).
class ScoreBreakdown(BaseModel):
    technical: float = Field(..., ge=0.0, le=10.0)
    architecture: float = Field(..., ge=0.0, le=10.0)
    product: float = Field(..., ge=0.0, le=10.0)
    communication: float = Field(..., ge=0.0, le=10.0)

    model_config = {"extra": "forbid"}

    @field_validator("technical", "architecture", "product", "communication", mode="before")
    @classmethod
    def _round_dim(cls, v: object) -> float:
        return round(float(v), 2)


# Bloco “Análise consolidada” (sem repetir literalmente a capa).
class ConsolidatedAnalysisBlock(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    attention_points: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


# Visão resumida por domínio (bullets curtos).
class DomainAnalysisBlock(BaseModel):
    backend: list[str] = Field(default_factory=list)
    frontend: list[str] = Field(default_factory=list)
    devops: list[str] = Field(default_factory=list)
    security: list[str] = Field(default_factory=list)
    behavioral: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


# Fit senioridade vs vaga.
class FitBlock(BaseModel):
    expected_level: str
    evaluated_level: str
    gap: int
    recommendation: str

    model_config = {"extra": "forbid"}


# Contrato completo devolvido pela IA e normalizado no backend.
class ExecutiveEvaluationReport(BaseModel):
    candidate: CandidateHeader
    decision: DecisionBlock
    highlights: HighlightsBlock
    summary: str
    score_breakdown: ScoreBreakdown
    consolidated_analysis: ConsolidatedAnalysisBlock
    domain_analysis: DomainAnalysisBlock = Field(default_factory=DomainAnalysisBlock)
    conflicts: list[str] = Field(default_factory=list)
    fit: FitBlock

    model_config = {"extra": "forbid"}
