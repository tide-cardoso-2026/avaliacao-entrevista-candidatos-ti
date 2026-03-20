"""API HTTP (FastAPI): scorecard, avaliacao por resposta, ranking e gap analysis."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.exceptions import EvidenceValidationError
from app.models.scorecard_models import (
    BatchEvaluateRequest,
    CorrelateEvaluationsRequest,
    EvaluateAnswerRequest,
    EvaluateAnswerResponse,
    GapAnalysis,
    GenerateScorecardRequest,
    Question,
    Scorecard,
)
from app.services.answer_evaluation_service import evaluate_answer
from app.services.correlation_service import correlate_evaluations
from app.services.evaluator_bias import evaluator_stats
from app.services.llm_service import OpenAILLMService
from app.services.question_bank import load_questions, load_situational_questions
from app.services.ranking_service import candidate_rankings_for_role
from app.services.scorecard_service import build_gap_analysis, build_scorecard
from app.services.scorecard_store import get_latest_scorecard, save_scorecard_snapshot

log = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


def get_llm_service() -> OpenAILLMService:
    return OpenAILLMService()


# Se `API_KEY` estiver definido no ambiente, exige o header `X-API-Key`.
def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = settings.API_KEY
    if not expected:
        return
    if not x_api_key or x_api_key.strip() != expected.strip():
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _rate_limit() -> str:
    return f"{max(1, settings.API_RATE_LIMIT_PER_MINUTE)}/minute"


class GenerateScorecardBody(GenerateScorecardRequest):
    role_slug: str | None = None
    persist: bool = True


def create_app() -> FastAPI:
    app = FastAPI(
        title="EntrevistaTaking — AI Candidate Evaluation",
        version="1.2.0",
        description="Scorecard padronizado, evidencia obrigatoria, calibracao e correlacao multi-pergunta.",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.post("/evaluate-answer", response_model=EvaluateAnswerResponse, dependencies=[Depends(require_api_key)])
    @limiter.limit(_rate_limit())
    def post_evaluate_answer(
        request: Request,
        body: EvaluateAnswerRequest,
        llm: Annotated[OpenAILLMService, Depends(get_llm_service)],
    ) -> EvaluateAnswerResponse:
        try:
            return evaluate_answer(
                llm=llm,
                question_id=body.questionId,
                question=body.question,
                candidate_answer=body.candidateAnswer,
                stack=body.stack,
                category=body.category,
            )
        except EvidenceValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post(
        "/evaluate-answer/batch", response_model=list[EvaluateAnswerResponse], dependencies=[Depends(require_api_key)]
    )
    @limiter.limit(_rate_limit())
    def post_evaluate_answer_batch(
        request: Request,
        body: BatchEvaluateRequest,
        llm: Annotated[OpenAILLMService, Depends(get_llm_service)],
    ) -> list[EvaluateAnswerResponse]:
        out: list[EvaluateAnswerResponse] = []
        for it in body.items:
            try:
                out.append(
                    evaluate_answer(
                        llm=llm,
                        question_id=it.questionId,
                        question=it.question,
                        candidate_answer=it.candidateAnswer,
                        stack=it.stack,
                        category=it.category,
                    )
                )
            except EvidenceValidationError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        return out

    @app.post("/generate-scorecard", response_model=Scorecard, dependencies=[Depends(require_api_key)])
    @limiter.limit(_rate_limit())
    def post_generate_scorecard(request: Request, body: GenerateScorecardBody) -> Scorecard:
        try:
            sc = build_scorecard(
                GenerateScorecardRequest(
                    candidateId=body.candidateId,
                    evaluatorId=body.evaluatorId,
                    dimensionScores=body.dimensionScores,
                    evidence=body.evidence,
                )
            )
        except EvidenceValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if body.persist:
            try:
                save_scorecard_snapshot(sc, role_slug=body.role_slug)
            except Exception as exc:
                log.exception("Failed to persist scorecard")
                raise HTTPException(status_code=503, detail="Failed to persist scorecard") from exc
        return sc

    @app.post("/correlate-evaluations", dependencies=[Depends(require_api_key)])
    @limiter.limit(_rate_limit())
    def post_correlate_evaluations(request: Request, body: CorrelateEvaluationsRequest) -> dict:
        return correlate_evaluations(body.evaluations)

    @app.get("/evaluators/{evaluator_id}/stats", dependencies=[Depends(require_api_key)])
    @limiter.limit(_rate_limit())
    def get_evaluator_stats(request: Request, evaluator_id: str) -> dict:
        st = evaluator_stats(evaluator_id)
        if not st:
            raise HTTPException(status_code=404, detail="No scorecards for this evaluator")
        return st.model_dump()

    @app.get("/candidate-ranking", dependencies=[Depends(require_api_key)])
    @limiter.limit(_rate_limit())
    def get_candidate_ranking(
        request: Request,
        role_slug: str | None = Query(default=None, description="Filtrar pela mesma vaga/funcao"),
    ) -> dict:
        rows = candidate_rankings_for_role(role_slug=role_slug)
        k = max(1, int(len(rows) * 0.1)) if rows else 0
        top = rows[:k]
        return {
            "rankings": [r.model_dump() for r in rows],
            "highlight_top_decile": [r.model_dump() for r in top],
        }

    @app.get("/gap-analysis/{candidate_id}", response_model=GapAnalysis, dependencies=[Depends(require_api_key)])
    @limiter.limit(_rate_limit())
    def get_gap_analysis(request: Request, candidate_id: str) -> GapAnalysis:
        sc = get_latest_scorecard(candidate_id)
        if not sc:
            raise HTTPException(status_code=404, detail="No scorecard found for candidate")
        return build_gap_analysis(sc)

    @app.get("/questions", response_model=list[Question], dependencies=[Depends(require_api_key)])
    @limiter.limit(_rate_limit())
    def get_questions(request: Request) -> list[Question]:
        return load_questions()

    @app.get("/questions/situational", response_model=list[Question], dependencies=[Depends(require_api_key)])
    @limiter.limit(_rate_limit())
    def get_situational(request: Request) -> list[Question]:
        return load_situational_questions()

    @app.get("/calibration/summary", dependencies=[Depends(require_api_key)])
    @limiter.limit(_rate_limit())
    def calibration_summary(request: Request) -> dict:
        return {
            "golden_dataset": "data/golden_dataset/golden_answers.json",
            "self_check": "If abs(aiScore - expectedScore) > 1 => calibrationFlag LOW_CONFIDENCE on /evaluate-answer",
            "evaluator_bias": "GET /evaluators/{evaluator_id}/stats",
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
