# AI Candidate Evaluation — mapeamento de requisitos

Este documento liga o **spec** (dimensões, scorecard, evidências, API) ao que está implementado no repositório.

## Dimensões e pesos

| Dimensão | Peso | Código |
|----------|------|--------|
| Technical | 0.4 | `app/core/dimensions.py` → `DIMENSION_WEIGHTS` |
| Architecture & System Design | 0.3 | idem |
| Product & Business | 0.2 | idem |
| Communication | 0.1 | idem |

`finalScore` = média ponderada no intervalo **1.0–5.0** (`weighted_dimension_score`).

## Scorecard e recomendação

- Modelos Pydantic: `app/models/scorecard_models.py` (`Scorecard`, `Evidence`, `DimensionScores`, …).
- Recomendação: `STRONG_HIRE` / `HIRE` / `NO_HIRE` via `recommendation_from_final_score` em `app/core/dimensions.py`
  (limiares ~4.25 / 3.0 — ajustáveis).

## Evidências por resposta

- `POST /evaluate-answer` chama `app/services/answer_evaluation_service.py` e devolve `AIScoreResult` + `Evidence`
  (justificativa **ancorada na resposta**; não inventar fatos externos — instrução no prompt).

## Question engine

- Banco JSON: `data/question_bank/sample_questions.json` (inclui **perguntas situacionais** obrigatórias).
- Loader: `app/services/question_bank.py` — `GET /questions`, `GET /questions/situational`.

## Gap analysis

- `GET /gap-analysis/{candidateId}` usa o último scorecard persistido e `build_gap_analysis` em `app/services/scorecard_service.py`.

## Ranking e percentil

- `GET /candidate-ranking` — `app/services/ranking_service.py` + tabela `scorecard_snapshots`.
- Campo `highlight_top_decile`: ~10% melhores notas.

## Persistência

- Tabela `scorecard_snapshots` em `app/db/models.py` (JSON completo do `Scorecard`).
- `evaluation_runs` continua para o fluxo de laudo multi-agente (pipeline).

## Calibração entre entrevistadores

- `GET /calibration/summary` — stub (agregação multi-avaliador ainda não implementada).

## Performance (< 3s por resposta)

- Meta operacional; não garantida por código. Reduza `MAX_TOKENS`, use modelo mais rápido ou fila assíncrona se necessário.

## API

- App FastAPI: `app/api/main.py`.
- Exemplo: `uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000`.

## Alta precisão (evidência obrigatória)

- `MIN_EVIDENCE_JUSTIFICATION_CHARS` (default 20): respostas de `/evaluate-answer` com justificativa curta demais retornam **422** (`EvidenceValidationError`).
- `SCORECARD_REQUIRE_EVIDENCE`: se `true`, `POST /generate-scorecard` exige ao menos um item em `evidence` com justificativa válida.
- **Golden dataset:** `data/golden_dataset/golden_answers.json` — se `abs(aiScore - expectedScore) > 1`, a resposta inclui `calibrationFlag: LOW_CONFIDENCE`.
- **Confidence:** `confidence.value` e `confidence.factors` em cada `/evaluate-answer`.
- **Senioridade:** `aiScore.seniorityDetail.level` (1–5) + `reasoning`.
- **Gaps estruturados:** `structuredGaps` em scorecard e em `GET /gap-analysis` (`category`, `severity`, `description`).
- **Correlação multi-pergunta:** `POST /correlate-evaluations` com corpo `{ "evaluations": [ ... ] }` — flags como `INCONSISTENT_PROFILE`.
- **Viés de avaliador:** `GET /evaluators/{evaluator_id}/stats` (média vs global, `biasLabel`).
- **Benchmark:** cada linha de ranking pode incluir `benchmark.comparedTo` (cohort).

## Integração com o pipeline multi-agente

- O CLI (`app/main.py`) e o `PipelineOrchestrator` **não** foram substituídos; o scorecard 1–5 é uma **camada adicional** para produtos/APIs que precisam do modelo do documento de requisitos.
