"""Contrato do pipeline: normalização, pesos por agente, conflitos e gatilho de deliberação."""

from __future__ import annotations

import re
from typing import Any

from app.models.schemas import AgentEvaluation, MiddleManagementEvaluation

# Pesos por palavra-chave no nome/domínio do assistente (ajuste fino por contexto de vaga).
DEFAULT_AGENT_WEIGHTS: dict[str, float] = {
    "backend": 1.2,
    "architecture": 1.2,
    "arquitetura": 1.2,
    "frontend": 0.8,
    "product": 1.0,
    "produto": 1.0,
    "sre": 1.1,
    "devops": 1.1,
    "data": 1.1,
    "dados": 1.1,
    "security": 1.1,
    "seguranca": 1.1,
}


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def _agent_weight(agent_name: str, domain: str, weights: dict[str, float]) -> float:
    blob = f"{agent_name} {domain}".lower()
    best = 1.0
    for key, w in weights.items():
        if key in blob:
            best = max(best, w)
    return best


def normalize_agent_evaluations(evals: list[AgentEvaluation]) -> list[AgentEvaluation]:
    """Clamp score/confidence e mantém weighted_score via modelo (computed)."""
    out: list[AgentEvaluation] = []
    for e in evals:
        out.append(
            e.model_copy(
                update={
                    "score": round(clamp(e.score, 0.0, 10.0), 2),
                    "confidence": round(clamp(e.confidence, 0.0, 1.0), 2),
                }
            )
        )
    return out


def compute_weighted_score_with_agent_weights(
    evaluations: list[AgentEvaluation],
    weights: dict[str, float] | None = None,
) -> float:
    """Média ponderada: score * confidence * peso(agente) / (confidence * peso)."""
    wmap = weights or DEFAULT_AGENT_WEIGHTS
    num = 0.0
    den = 0.0
    for e in evaluations:
        w = _agent_weight(e.agent_name, e.domain, wmap)
        num += e.score * e.confidence * w
        den += e.confidence * w
    if den == 0:
        return 0.0
    return round(num / den, 2)


def deliberation_should_run(
    managers: list[MiddleManagementEvaluation],
    *,
    score_threshold: float = 1.5,
) -> bool:
    """Dispara deliberação se spread de score > limiar ou qualquer conflito explícito."""
    if len(managers) < 2:
        return False
    scores = [m.score_consolidated for m in managers]
    if max(scores) - min(scores) > score_threshold:
        return True
    for m in managers:
        if m.conflicts:
            return True
    return False


def detect_manager_pair_conflicts(
    managers: list[MiddleManagementEvaluation],
    *,
    roles: list[str] | None = None,
    spread_threshold: float = 2.0,
) -> list[dict[str, Any]]:
    """Pares de managers com divergência de score acima do limiar."""
    conflicts: list[dict[str, Any]] = []
    n = len(managers)

    def _label(idx: int) -> str:
        if roles and idx < len(roles):
            return roles[idx]
        return f"manager_{idx}"

    for i in range(n):
        for j in range(i + 1, n):
            si = managers[i].score_consolidated
            sj = managers[j].score_consolidated
            if abs(si - sj) > spread_threshold:
                conflicts.append(
                    {
                        "agents": [_label(i), _label(j)],
                        "type": "score_divergence",
                        "spread": round(abs(si - sj), 2),
                    }
                )
    return conflicts


def extract_high_severity_risks(
    managers: list[MiddleManagementEvaluation],
) -> list[dict[str, str]]:
    """Riscos high dos managers (dedupe por descrição)."""
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for m in managers:
        for r in m.structured_risks:
            if r.severity != "high":
                continue
            key = re.sub(r"\s+", " ", r.description.strip().lower())
            if not key or key in seen:
                continue
            seen.add(key)
            out.append({"description": r.description, "severity": r.severity})
    return out
