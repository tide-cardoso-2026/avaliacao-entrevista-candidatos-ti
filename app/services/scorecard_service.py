"""Montagem de scorecard, gaps estruturados e recomendacao a partir das dimensoes 1-5."""

from __future__ import annotations

from app.core.config import settings
from app.core.dimensions import recommendation_from_final_score, weighted_dimension_score
from app.core.evidence_validation import validate_evidence_list
from app.models.scorecard_models import (
    DimensionScores,
    GapAnalysis,
    GapItem,
    GapSeverity,
    GenerateScorecardRequest,
    Scorecard,
)


def _sev(x: float) -> GapSeverity:
    if x < 2.5:
        return "high"
    if x < 3.0:
        return "medium"
    return "low"


# Gaps textuais e estruturados quando dimensao abaixo do patamar.
def _gaps_from_dimensions(ds: DimensionScores, threshold: float = 3.0) -> tuple[list[str], list[GapItem]]:
    gaps: list[str] = []
    structured: list[GapItem] = []
    if ds.technical < threshold:
        gaps.append("Technical skills below expected bar for the role")
        structured.append(
            GapItem(
                category="Technical",
                severity=_sev(ds.technical),
                description="Technical depth or specificity below bar",
            )
        )
    if ds.architecture < threshold:
        gaps.append("Architecture and system design need strengthening")
        structured.append(
            GapItem(
                category="Architecture",
                severity=_sev(ds.architecture),
                description="Cannot explain trade-offs or scalability considerations adequately",
            )
        )
    if ds.product < threshold:
        gaps.append("Product and business thinking are limited")
        structured.append(
            GapItem(
                category="Product",
                severity=_sev(ds.product),
                description="Limited product or stakeholder alignment signals",
            )
        )
    if ds.communication < threshold:
        gaps.append("Communication clarity or structure needs improvement")
        structured.append(
            GapItem(
                category="Communication",
                severity=_sev(ds.communication),
                description="Clarity or structure of reasoning below bar",
            )
        )
    return gaps, structured


# Constroi scorecard completo com media ponderada e recomendacao.
def build_scorecard(req: GenerateScorecardRequest) -> Scorecard:
    if settings.SCORECARD_REQUIRE_EVIDENCE:
        validate_evidence_list(req.evidence, min_items=1)

    ds = req.dimensionScores
    final = weighted_dimension_score(
        technical=ds.technical,
        architecture=ds.architecture,
        product=ds.product,
        communication=ds.communication,
    )
    rec = recommendation_from_final_score(final)
    gaps, structured = _gaps_from_dimensions(ds)
    return Scorecard(
        candidateId=req.candidateId,
        evaluatorId=req.evaluatorId,
        dimensionScores=ds,
        finalScore=final,
        recommendation=rec,
        evidence=req.evidence,
        gaps=gaps,
        structuredGaps=structured,
    )


# Resumo de lacunas e texto de recomendacao para contratacao.
def build_gap_analysis(scorecard: Scorecard) -> GapAnalysis:
    if scorecard.gaps:
        summary = "Main gaps: " + "; ".join(scorecard.gaps[:6])
    else:
        summary = "No dimension fell below the default threshold; review evidence for nuance."
    hire = scorecard.recommendation
    if hire == "STRONG_HIRE":
        rec = "Strong hire signal based on weighted dimensions; validate with live interview."
    elif hire == "HIRE":
        rec = "Hire possible; confirm gaps in follow-up where dimensions are borderline."
    else:
        rec = "Do not hire based on current structured scores; reassess if new evidence is added."
    return GapAnalysis(
        gaps=list(scorecard.gaps),
        structuredGaps=list(scorecard.structuredGaps),
        summary=summary,
        hiringRecommendation=rec,
    )
