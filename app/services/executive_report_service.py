"""Gera o relatório executivo (JSON) a partir das avaliações, com normalização e fallback."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from app.core.protocols import LLMService
from app.models.executive_report import (
    CandidateHeader,
    ConsolidatedAnalysisBlock,
    DecisionBlock,
    DomainAnalysisBlock,
    ExecutiveEvaluationReport,
    FitBlock,
    HighlightsBlock,
    ScoreBreakdown,
)
from app.models.schemas import AgentEvaluation, CTOFinalEvaluation, FinalIndication, MiddleManagementEvaluation

log = logging.getLogger(__name__)

_Rec = Literal["STRONG_HIRE", "HIRE", "NO_HIRE"]
_Lev = Literal["junior", "mid", "senior", "staff"]

WEIGHT_TECHNICAL = 0.4
WEIGHT_ARCHITECTURE = 0.3
WEIGHT_PRODUCT = 0.2
WEIGHT_COMMUNICATION = 0.1

_MAX_LIST = 5
_PROMPT_PATH = Path("prompts") / "executive_report.md"


# Ponderação oficial do score final (dimensões 0–10).
def weighted_final_score(b: ScoreBreakdown) -> float:
    return round(
        b.technical * WEIGHT_TECHNICAL
        + b.architecture * WEIGHT_ARCHITECTURE
        + b.product * WEIGHT_PRODUCT
        + b.communication * WEIGHT_COMMUNICATION,
        2,
    )


# Remove duplicatas preservando ordem (comparação case-insensitive).
def dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        s = (it or "").strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


# Limita o tamanho das listas de bullets.
def cap_list(items: list[str], *, max_items: int = _MAX_LIST) -> list[str]:
    return dedupe_strings(items)[:max_items]


# Remove trechos que parecem JSON bruto colado pelo modelo.
def strip_json_noise(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) > 4000 and ("{" in t[:200] and "}" in t[-200:]):
        return re.sub(r"\{[^{}]*\}", "", t)[:2000] or t[:2000]
    return t


# Normaliza listas, scores e alinha `decision.score` à fórmula ponderada.
def normalize_executive_report(report: ExecutiveEvaluationReport) -> ExecutiveEvaluationReport:
    h = report.highlights
    highlights = HighlightsBlock(
        strengths=cap_list(h.strengths),
        gaps=cap_list(h.gaps),
        risks=cap_list(h.risks),
    )
    ca = report.consolidated_analysis
    consolidated = ConsolidatedAnalysisBlock(
        strengths=cap_list(ca.strengths),
        attention_points=cap_list(ca.attention_points),
        risks=cap_list(ca.risks),
    )
    dom = report.domain_analysis
    domain = DomainAnalysisBlock(
        backend=cap_list(dom.backend),
        frontend=cap_list(dom.frontend),
        devops=cap_list(dom.devops),
        security=cap_list(dom.security),
        behavioral=cap_list(dom.behavioral),
    )
    conflicts = cap_list(report.conflicts, max_items=5)
    wf = weighted_final_score(report.score_breakdown)
    d = report.decision.model_copy(update={"score": wf})
    summary = strip_json_noise(report.summary)[:2500]
    return report.model_copy(
        update={
            "highlights": highlights,
            "consolidated_analysis": consolidated,
            "domain_analysis": domain,
            "conflicts": conflicts,
            "decision": d,
            "summary": summary,
        }
    )


# Monta texto compacto para o prompt (sem JSON de análises aninhadas).
def build_raw_evaluation_payload(
    *,
    vaga: str,
    candidato_display: str,
    assistant_evaluations: list[AgentEvaluation],
    middle: MiddleManagementEvaluation,
    cto: CTOFinalEvaluation,
) -> str:
    assistants_compact = [
        {
            "agent_name": e.agent_name,
            "domain": e.domain,
            "score": e.score,
            "confidence": e.confidence,
            "strengths": e.strengths[:5],
            "improvements": e.improvements[:5],
            "risks": e.risks[:5],
            "recommendation": (e.recommendation or "")[:500],
        }
        for e in assistant_evaluations
    ]
    middle_block = {
        "score_consolidated": middle.score_consolidated,
        "confidence": middle.confidence,
        "hire_recommendation": middle.hire_recommendation,
        "final_recommendation": middle.final_recommendation,
        "conflicts": middle.conflicts[:10],
        "critical_questions": middle.critical_questions[:10],
        "divergence_flags": [f.model_dump() for f in middle.divergence_flags][:5],
        "key_strengths": middle.key_strengths[:8],
        "key_gaps": middle.key_gaps[:8],
        "missing_evidence": middle.missing_evidence[:12],
        "structured_risks": [r.model_dump() for r in middle.structured_risks][:15],
        "calibration_notes_excerpt": (middle.calibration_notes or "")[:2000],
        "analysis_excerpt": (middle.analysis or "")[:4000],
    }
    cto_block = {
        "final_rating": cto.final_rating.value,
        "score_final": cto.score_final,
        "final_indication": cto.final_indication.value,
        "confidence": cto.confidence,
        "risks": [r.model_dump() for r in cto.risks][:15],
        "tradeoffs": cto.tradeoffs[:12],
        "layers": {
            "strategic": cto.strategic_analysis.model_dump(),
            "tactical": cto.tactical_analysis.model_dump(),
            "operational": cto.operational_analysis.model_dump(),
        },
        "observations_excerpt": strip_json_noise(cto.observations or "")[:3000],
    }
    return json.dumps(
        {
            "position_title": vaga,
            "candidate_display": candidato_display,
            "assistants": assistants_compact,
            "middle_management": middle_block,
            "cto": cto_block,
        },
        ensure_ascii=False,
    )


# Mapeia indicação do CTO para código de recomendação executiva.
def _indication_to_recommendation(ind: FinalIndication) -> str:
    if ind == FinalIndication.Reprovar:
        return "NO_HIRE"
    if ind == FinalIndication.AprovarComRessalvas:
        return "HIRE"
    return "STRONG_HIRE"


# Heurística de nível textual a partir do rating do CTO.
def _rating_to_level_code(rating_value: str) -> str:
    r = (rating_value or "").lower()
    if "estagi" in r or "junior" in r:
        return "junior"
    if "pleno" in r or "mid" in r:
        return "mid"
    if "senior" in r:
        return "senior"
    if "especialista" in r or "staff" in r:
        return "staff"
    return "mid"


# Heurística de domínio a partir do nome do agente / domínio.
def _domain_buckets(evals: list[AgentEvaluation]) -> DomainAnalysisBlock:
    backend: list[str] = []
    frontend: list[str] = []
    devops: list[str] = []
    security: list[str] = []
    behavioral: list[str] = []

    for e in evals:
        name = (e.agent_name + " " + e.domain).lower()
        line = f"{e.domain}: score {e.score:.1f}"
        if any(x in name for x in ("backend", "fullstack", "engenheiro", "data")):
            backend.extend([line, *e.strengths[:2]])
        elif any(x in name for x in ("frontend", "ux", "ui")):
            frontend.extend([line, *e.strengths[:2]])
        elif any(x in name for x in ("devops", "sre", "infra")):
            devops.extend([line, *e.strengths[:2]])
        elif any(x in name for x in ("sec", "security")):
            security.extend([line, *e.strengths[:2]])
        elif any(x in name for x in ("psic", "rh", "cultura", "agil", "product", "po")):
            behavioral.extend([line, *e.strengths[:2]])
        else:
            backend.append(line)

    return DomainAnalysisBlock(
        backend=cap_list(backend, max_items=5),
        frontend=cap_list(frontend, max_items=5),
        devops=cap_list(devops, max_items=5),
        security=cap_list(security, max_items=5),
        behavioral=cap_list(behavioral, max_items=5),
    )


# Fallback determinístico se a chamada LLM falhar.
def build_fallback_executive_report(
    *,
    vaga: str,
    candidato_display: str,
    assistant_evaluations: list[AgentEvaluation],
    middle: MiddleManagementEvaluation,
    cto: CTOFinalEvaluation,
) -> ExecutiveEvaluationReport:
    today = datetime.now().strftime("%Y-%m-%d")
    sf = float(cto.score_final)
    sb = ScoreBreakdown(
        technical=round(min(10.0, max(0.0, sf)), 2),
        architecture=round(min(10.0, max(0.0, sf - 0.3)), 2),
        product=round(min(10.0, max(0.0, sf - 0.5)), 2),
        communication=round(min(10.0, max(0.0, sf - 0.7)), 2),
    )
    wf = weighted_final_score(sb)
    rec = _indication_to_recommendation(cto.final_indication)
    lvl = _rating_to_level_code(cto.final_rating.value)

    strengths = dedupe_strings([*middle.conflicts[:1], *[s for e in assistant_evaluations for s in e.strengths][:8]])[
        :5
    ]
    gaps = dedupe_strings([i for e in assistant_evaluations for i in e.improvements][:8])[:5]
    cto_risk_lines = [f"[{r.impact}/{r.probability}] {r.description}" for r in cto.risks]
    risks = dedupe_strings([*cto_risk_lines, *[r for e in assistant_evaluations for r in e.risks]][:10])[:5]

    summary = (
        f"Síntese automática: indicação {cto.final_indication.value}, score consolidado {wf:.1f}/10. "
        f"Ver análise por domínio e conflitos entre avaliadores quando houver."
    )

    consolidated = ConsolidatedAnalysisBlock(
        strengths=strengths[:5],
        attention_points=gaps[:5],
        risks=risks[:5],
    )
    dom = _domain_buckets(assistant_evaluations)
    conflicts = cap_list(
        [f.description for f in middle.divergence_flags] + middle.conflicts,
        max_items=5,
    )

    fit = FitBlock(
        expected_level="(definir conforme vaga)",
        evaluated_level=cto.final_rating.value,
        gap=0,
        recommendation="Ajustar expectativa de senioridade ou detalhar requisitos da vaga.",
    )

    return ExecutiveEvaluationReport(
        candidate=CandidateHeader(name=candidato_display, role=vaga, date=today),
        decision=DecisionBlock(
            recommendation=cast(_Rec, rec),
            level=cast(_Lev, lvl),
            score=wf,
            confidence=round(float(cto.confidence), 2),
        ),
        highlights=HighlightsBlock(strengths=strengths, gaps=gaps, risks=risks),
        summary=summary,
        score_breakdown=sb,
        consolidated_analysis=consolidated,
        domain_analysis=dom,
        conflicts=conflicts,
        fit=fit,
    )


# Ajusta respostas comuns do modelo (None em listas, gap decimal) antes da validação.
def _sanitize_executive_payload(payload: dict) -> dict:
    p = dict(payload)
    da = p.get("domain_analysis")
    if not isinstance(da, dict):
        da = {}
    nda = dict(da)
    for k in ("backend", "frontend", "devops", "security", "behavioral"):
        v = nda.get(k)
        nda[k] = v if isinstance(v, list) else []
    p["domain_analysis"] = nda
    fit = p.get("fit")
    if isinstance(fit, dict):
        fit = dict(fit)
        g = fit.get("gap")
        if isinstance(g, float):
            fit["gap"] = int(round(g))
        elif g is not None and not isinstance(g, int):
            try:
                fit["gap"] = int(round(float(g)))
            except (TypeError, ValueError):
                fit["gap"] = 0
        p["fit"] = fit
    return p


# Converte payload do LLM (com aliases) para o modelo Pydantic.
def _coerce_payload(payload: dict) -> ExecutiveEvaluationReport:
    if "consolidated_analysis" not in payload and "consolidatedAnalysis" in payload:
        payload = payload | {"consolidated_analysis": payload.get("consolidatedAnalysis")}
    ca = payload.get("consolidated_analysis") or {}
    if isinstance(ca, dict) and "attention_points" not in ca and "attentionPoints" in ca:
        ca = dict(ca) | {"attention_points": ca.get("attentionPoints")}
    payload = dict(payload)
    payload["consolidated_analysis"] = ca
    payload = _sanitize_executive_payload(payload)
    return ExecutiveEvaluationReport.model_validate(payload)


# Gera o relatório executivo via LLM; em falha usa fallback determinístico.
def build_executive_report(
    llm: LLMService,
    *,
    vaga: str,
    candidato_display: str,
    assistant_evaluations: list[AgentEvaluation],
    middle: MiddleManagementEvaluation,
    cto: CTOFinalEvaluation,
) -> ExecutiveEvaluationReport:
    raw = build_raw_evaluation_payload(
        vaga=vaga,
        candidato_display=candidato_display,
        assistant_evaluations=assistant_evaluations,
        middle=middle,
        cto=cto,
    )
    if not _PROMPT_PATH.is_file():
        log.debug("Prompt executive_report missing; using fallback")
        return normalize_executive_report(
            build_fallback_executive_report(
                vaga=vaga,
                candidato_display=candidato_display,
                assistant_evaluations=assistant_evaluations,
                middle=middle,
                cto=cto,
            )
        )

    template = _PROMPT_PATH.read_text(encoding="utf-8", errors="ignore")
    prompt = template.replace("{{RAW_EVALUATION_DATA}}", raw)

    try:
        payload = llm.generate_json(prompt=prompt, context="", layer="cto")
        report = _coerce_payload(payload)
        return normalize_executive_report(report)
    except Exception:
        log.debug("Relatório executivo: ajuste automático do texto gerado (detalhe técnico abaixo)", exc_info=True)
        return normalize_executive_report(
            build_fallback_executive_report(
                vaga=vaga,
                candidato_display=candidato_display,
                assistant_evaluations=assistant_evaluations,
                middle=middle,
                cto=cto,
            )
        )
