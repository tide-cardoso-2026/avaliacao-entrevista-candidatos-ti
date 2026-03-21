"""Modelos do scorecard padronizado, evidencias obrigatorias e alta precisao."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

Seniority = Literal["junior", "mid", "senior", "staff"]
QuestionCategory = Literal["technical", "architecture", "product", "behavioral"]
Recommendation = Literal["STRONG_HIRE", "HIRE", "NO_HIRE"]
GapSeverity = Literal["low", "medium", "high"]


# --- Question engine ---


class ExpectedAnswerLevels(BaseModel):

    model_config = ConfigDict(extra="forbid")

    level3: str = Field(description="Resposta nível intermediário")
    level4: str = Field(description="Resposta nível avançado")
    level5: str = Field(description="Resposta nível expert")


class Question(BaseModel):

    model_config = ConfigDict(extra="forbid")

    id: str
    stack: str = Field(description="Ex.: backend, frontend, devops")
    seniority: Seniority
    category: QuestionCategory
    prompt: str
    expectedAnswer: ExpectedAnswerLevels
    evaluationCriteria: list[str] = Field(default_factory=list)
    situational: bool = Field(default=False, description="Pergunta cenário (obrigatório no banco ter exemplos)")


# --- Evidence & scoring (spec: answer + signalsExtracted aliases) ---


class Evidence(BaseModel):

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    questionId: str
    question: str
    candidateAnswer: str = Field(validation_alias=AliasChoices("answer", "candidateAnswer"))
    extractedSignals: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("signalsExtracted", "extractedSignals"),
    )
    score: float = Field(ge=1.0, le=5.0)
    justification: str


class SeniorityScore(BaseModel):

    model_config = ConfigDict(extra="forbid")

    level: int = Field(ge=1, le=5, description="1 superficial ... 5 expert")
    reasoning: str


class ConfidenceScore(BaseModel):

    model_config = ConfigDict(extra="forbid")

    value: float = Field(ge=0.0, le=1.0)
    factors: list[str] = Field(default_factory=list)


class AIScoreResult(BaseModel):

    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=1.0, le=5.0)
    seniorityLevelDetected: float = Field(ge=1.0, le=5.0)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    justification: str
    missingElements: list[str] = Field(default_factory=list)
    antiPatterns: list[str] = Field(default_factory=list)
    seniorityDetail: SeniorityScore | None = None


class DimensionScores(BaseModel):

    model_config = ConfigDict(extra="forbid")

    technical: float = Field(ge=1.0, le=5.0)
    architecture: float = Field(ge=1.0, le=5.0)
    product: float = Field(ge=1.0, le=5.0)
    communication: float = Field(ge=1.0, le=5.0)

    @field_validator("technical", "architecture", "product", "communication")
    @classmethod
    def _round(cls, v: float) -> float:
        return round(float(v), 2)


class GapItem(BaseModel):

    model_config = ConfigDict(extra="forbid")

    category: str
    severity: GapSeverity
    description: str


class Benchmark(BaseModel):

    model_config = ConfigDict(extra="forbid")

    percentile: float = Field(ge=0.0, le=100.0)
    comparedTo: str = Field(description="Ex.: role_slug ou cohort")


class Scorecard(BaseModel):

    model_config = ConfigDict(extra="forbid")

    candidateId: str
    evaluatorId: str
    dimensionScores: DimensionScores
    finalScore: float = Field(ge=1.0, le=5.0)
    recommendation: Recommendation
    evidence: list[Evidence] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    structuredGaps: list[GapItem] = Field(default_factory=list)


class GapAnalysis(BaseModel):

    model_config = ConfigDict(extra="forbid")

    gaps: list[str]
    structuredGaps: list[GapItem] = Field(default_factory=list)
    summary: str
    hiringRecommendation: str


class CandidateRanking(BaseModel):

    model_config = ConfigDict(extra="forbid")

    candidateId: str
    finalScore: float
    percentile: float = Field(ge=0.0, le=100.0)
    benchmark: Benchmark | None = None


# --- API payloads ---


class EvaluateAnswerRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    questionId: str
    question: str
    candidateAnswer: str
    stack: str = "general"
    category: QuestionCategory = "technical"


class EvaluateAnswerResponse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    aiScore: AIScoreResult
    evidence: Evidence
    confidence: ConfidenceScore
    calibrationFlag: str | None = None
    goldenExpectedScore: float | None = None
    goldenExplanation: str | None = None


class GenerateScorecardRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    candidateId: str
    evaluatorId: str = "system"
    dimensionScores: DimensionScores
    evidence: list[Evidence] = Field(default_factory=list)


class BatchEvaluateItem(BaseModel):

    model_config = ConfigDict(extra="forbid")

    questionId: str
    question: str
    candidateAnswer: str
    stack: str = "general"
    category: QuestionCategory = "technical"


class BatchEvaluateRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    items: list[BatchEvaluateItem] = Field(min_length=1)


class CorrelateEvaluationsRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    evaluations: list[EvaluateAnswerResponse] = Field(min_length=2)
