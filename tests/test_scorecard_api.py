"""Testes do scorecard (dimensoes), API FastAPI e persistencia opcional."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import app, create_app, get_llm_service
from app.core.config import settings
from app.core.dimensions import weighted_dimension_score
from app.db.session import reset_engine
from app.models.scorecard_models import DimensionScores, Evidence, GenerateScorecardRequest
from app.services.scorecard_service import build_gap_analysis, build_scorecard


def test_weighted_dimension_score_formula() -> None:
    s = weighted_dimension_score(
        technical=5.0,
        architecture=4.0,
        product=3.0,
        communication=2.0,
    )
    assert s == pytest.approx(5 * 0.4 + 4 * 0.3 + 3 * 0.2 + 2 * 0.1, rel=1e-3)


def _sample_evidence() -> list[Evidence]:
    return [
        Evidence(
            questionId="q1",
            question="Pergunta",
            candidateAnswer="Resposta",
            extractedSignals=["sinal"],
            score=4.0,
            justification="Justificativa com mais de vinte caracteres obrigatorios para evidencia.",
        )
    ]


def test_build_scorecard_recommendation() -> None:
    sc = build_scorecard(
        GenerateScorecardRequest(
            candidateId="c1",
            evaluatorId="e1",
            dimensionScores=DimensionScores(
                technical=4.5,
                architecture=4.0,
                product=3.5,
                communication=4.0,
            ),
            evidence=_sample_evidence(),
        )
    )
    assert 1.0 <= sc.finalScore <= 5.0
    assert sc.recommendation in ("STRONG_HIRE", "HIRE", "NO_HIRE")
    assert sc.structuredGaps is not None
    ga = build_gap_analysis(sc)
    assert ga.summary
    assert ga.hiringRecommendation
    assert isinstance(ga.structuredGaps, list)


class _FakeLLM:
    def generate_json(
        self,
        *,
        prompt: str,
        context: str,
        layer: str = "assistants",
        assistant_model_tier: str | None = None,
        system_preamble: str | None = None,
    ) -> dict:
        return {
            "score": 4.0,
            "seniorityLevel": 4,
            "seniorityReasoning": "Nivel solido pois cita conceitos concretos e passos operacionais.",
            "strengths": ["Clareza"],
            "weaknesses": [],
            "justification": (
                "A resposta demonstra compreensao adequada do tema e cita elementos concretos "
                "da propria experiencia profissional em producao."
            ),
            "extractedSignals": ["trade-off"],
            "missingElements": [],
            "antiPatterns": [],
        }


class _ShortJustLLM:
    def generate_json(
        self,
        *,
        prompt: str,
        context: str,
        layer: str = "assistants",
        assistant_model_tier: str | None = None,
        system_preamble: str | None = None,
    ) -> dict:
        return {
            "score": 3.0,
            "seniorityLevel": 2,
            "seniorityReasoning": "x",
            "strengths": [],
            "weaknesses": [],
            "justification": "curta",
            "extractedSignals": [],
            "missingElements": [],
            "antiPatterns": ["generic_answer"],
        }


def test_evaluate_answer_rejects_short_justification() -> None:
    a = create_app()
    a.dependency_overrides[get_llm_service] = lambda: _ShortJustLLM()
    client = TestClient(a)
    r = client.post(
        "/evaluate-answer",
        json={
            "questionId": "q1",
            "question": "Q",
            "candidateAnswer": "A",
            "stack": "backend",
            "category": "technical",
        },
    )
    assert r.status_code == 422
    a.dependency_overrides.clear()


def test_evaluate_answer_endpoint() -> None:
    a = create_app()
    a.dependency_overrides[get_llm_service] = lambda: _FakeLLM()
    client = TestClient(a)
    r = client.post(
        "/evaluate-answer",
        json={
            "questionId": "q1",
            "question": "Explique idempotencia.",
            "candidateAnswer": "Uso chave de idempotencia e deduplico.",
            "stack": "backend",
            "category": "technical",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["aiScore"]["score"] == 4.0
    assert data["evidence"]["questionId"] == "q1"
    assert data["confidence"]["value"] >= 0.0
    assert "seniorityDetail" in data["aiScore"] or data["aiScore"].get("seniorityLevelDetected")
    a.dependency_overrides.clear()


def test_generate_scorecard_no_persist() -> None:
    client = TestClient(app)
    r = client.post(
        "/generate-scorecard",
        json={
            "candidateId": "c-x",
            "evaluatorId": "e1",
            "dimensionScores": {
                "technical": 4.0,
                "architecture": 3.0,
                "product": 3.0,
                "communication": 4.0,
            },
            "evidence": [
                {
                    "questionId": "q1",
                    "question": "Q",
                    "candidateAnswer": "A",
                    "extractedSignals": ["x"],
                    "score": 4.0,
                    "justification": "Texto longo o suficiente para justificar a nota com evidencia.",
                }
            ],
            "persist": False,
        },
    )
    assert r.status_code == 200
    assert r.json()["candidateId"] == "c-x"


def test_gap_analysis_404() -> None:
    client = TestClient(app)
    r = client.get("/gap-analysis/nonexistent-candidate-xyz")
    assert r.status_code == 404


def test_questions_list() -> None:
    client = TestClient(app)
    r = client.get("/questions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    situ = client.get("/questions/situational")
    assert situ.status_code == 200
    assert all(q.get("situational") is True for q in situ.json())


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'sc.db'}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    reset_engine()
    yield
    reset_engine()


def test_persist_and_gap(isolated_db, tmp_path) -> None:
    client = TestClient(app)
    r = client.post(
        "/generate-scorecard",
        json={
            "candidateId": "c-persist",
            "evaluatorId": "e1",
            "dimensionScores": {
                "technical": 4.0,
                "architecture": 3.0,
                "product": 3.0,
                "communication": 4.0,
            },
            "evidence": [
                {
                    "questionId": "q1",
                    "question": "Q",
                    "candidateAnswer": "A",
                    "extractedSignals": ["x"],
                    "score": 4.0,
                    "justification": "Texto longo o suficiente para justificar a nota com evidencia.",
                }
            ],
            "persist": True,
            "role_slug": "backend-mid",
        },
    )
    assert r.status_code == 200
    g = client.get("/gap-analysis/c-persist")
    assert g.status_code == 200
    assert g.json()["gaps"] is not None
    assert "structuredGaps" in g.json()


def test_correlate_endpoint() -> None:
    client = TestClient(app)
    a = create_app()
    a.dependency_overrides[get_llm_service] = lambda: _FakeLLM()
    c = TestClient(a)
    r1 = c.post(
        "/evaluate-answer",
        json={
            "questionId": "a",
            "question": "Q1",
            "candidateAnswer": "long answer " * 10,
            "stack": "backend",
            "category": "technical",
        },
    )
    r2 = c.post(
        "/evaluate-answer",
        json={
            "questionId": "b",
            "question": "Q2",
            "candidateAnswer": "other " * 10,
            "stack": "backend",
            "category": "technical",
        },
    )
    assert r1.status_code == 200 and r2.status_code == 200
    corr = client.post(
        "/correlate-evaluations",
        json={"evaluations": [r1.json(), r2.json()]},
    )
    assert corr.status_code == 200
    assert "flags" in corr.json()
    a.dependency_overrides.clear()
