"""Avaliacao de uma resposta do candidato via LLM (evidencia obrigatoria + confidence + golden check)."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.evidence_validation import validate_evidence
from app.core.exceptions import EvidenceValidationError
from app.core.protocols import LLMService
from app.models.scorecard_models import (
    AIScoreResult,
    ConfidenceScore,
    EvaluateAnswerResponse,
    Evidence,
    SeniorityScore,
)
from app.services.confidence_scoring import build_confidence
from app.services.golden_dataset import golden_self_check

log = logging.getLogger(__name__)

_EVAL_PROMPT = """Voce e um entrevistador tecnico senior (modo ALTA PRECISAO).

Regras obrigatorias:
- Avalie usando APENAS o texto da resposta. Nao assuma conhecimento nao explicitado.
- Penalize respostas genericas, buzzwords sem explicacao e falta de exemplos concretos.
- Valorize trade-offs, profundidade e clareza.
- Se a resposta for vaga, a nota deve refletir isso (tipicamente 1-2).

Categoria: {category}
Stack: {stack}

Pergunta:
{question}

Resposta do candidato:
{candidate_answer}

Retorne UM objeto JSON com as chaves exatas:
- "score": numero 1-5
- "seniorityLevel": inteiro 1-5 (1 superficial, 2 basico, 3 solido, 4 avancado, 5 expert com trade-offs e casos reais)
- "seniorityReasoning": string (por que esse nivel, citando a resposta)
- "strengths": array de strings
- "weaknesses": array de strings
- "justification": string longa (minimo 20 caracteres) explicando a nota com referencia ao texto
- "extractedSignals": array (profundidade, trade-offs, experiencia real, clareza — apenas o que o texto sustenta)
- "missingElements": array (o que faltou para nota maxima)
- "antiPatterns": array (ex.: "generic_answer", "buzzwords_without_detail", "no_real_example" — so se aplicavel)
"""


# Chama o modelo, monta evidencia e rejeita se justificativa invalida.
def evaluate_answer(
    *,
    llm: LLMService,
    question_id: str,
    question: str,
    candidate_answer: str,
    stack: str,
    category: str,
) -> EvaluateAnswerResponse:
    prompt = _EVAL_PROMPT.format(
        category=category,
        stack=stack,
        question=question.strip(),
        candidate_answer=candidate_answer.strip(),
    )
    payload = llm.generate_json(
        prompt=prompt,
        context="",
        layer="assistants",
        assistant_model_tier="technical",
    )

    score = float(payload.get("score", 3))
    score = max(1.0, min(5.0, score))

    s_level = int(round(float(payload.get("seniorityLevel", payload.get("seniorityLevelDetected", score)))))
    s_level = max(1, min(5, s_level))
    s_reason = str(payload.get("seniorityReasoning", "")).strip() or "Sem raciocinio de senioridade retornado."
    seniority_detail = SeniorityScore(level=s_level, reasoning=s_reason)

    strengths = _as_list(payload.get("strengths"))
    weaknesses = _as_list(payload.get("weaknesses"))
    signals = _as_list(payload.get("extractedSignals"))
    missing = _as_list(payload.get("missingElements"))
    anti = _as_list(payload.get("antiPatterns"))

    justification = str(payload.get("justification", "")).strip()
    if len(justification) < settings.MIN_EVIDENCE_JUSTIFICATION_CHARS:
        raise EvidenceValidationError(
            "Model returned justification shorter than minimum; retry or use a stronger model. "
            f"Required {settings.MIN_EVIDENCE_JUSTIFICATION_CHARS} chars."
        )

    ai = AIScoreResult(
        score=score,
        seniorityLevelDetected=float(s_level),
        strengths=strengths,
        weaknesses=weaknesses,
        justification=justification,
        missingElements=missing,
        antiPatterns=anti,
        seniorityDetail=seniority_detail,
    )
    ev = Evidence(
        questionId=question_id,
        question=question.strip(),
        candidateAnswer=candidate_answer.strip(),
        extractedSignals=signals,
        score=score,
        justification=justification,
    )
    validate_evidence(ev)

    conf = build_confidence(
        answer_text=candidate_answer,
        justification=justification,
        signals=signals,
        weaknesses=weaknesses,
        anti_patterns=anti,
    )

    calib_flag, golden = golden_self_check(ai_score=score, question_id=question_id)
    g_exp = golden.expectedScore if golden else None
    g_expl = golden.explanation if golden else None

    return EvaluateAnswerResponse(
        aiScore=ai,
        evidence=ev,
        confidence=conf,
        calibrationFlag=calib_flag,
        goldenExpectedScore=g_exp,
        goldenExplanation=g_expl,
    )


def _as_list(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if not isinstance(raw, list):
        return [str(raw).strip()] if str(raw).strip() else []
    out: list[str] = []
    for x in raw:
        if x is not None and str(x).strip():
            out.append(str(x).strip())
    return out
