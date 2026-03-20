# Testes de staging (pré-core)

Camada **intermediária** para validar contratos e arquivos de dados **sem** depender do pipeline completo (`test_pipeline.py`).

## O que entra aqui

- Formato da base técnica (`data/technical-questions/*.md`)
- **`test_assistants_backend_kb_evaluation.py`** — só `AgentEngine` com **Dev Backend**, usando `backend.md` + `assistant_evaluation.md` no contexto (sem orchestrator / middle / CTO). Ao passar, gera PDF em **`staging/output/`** (nome tipo `staging_assistants_*_*.pdf`; arquivos `.pdf` ignorados no git).
- Outros contratos de dados ou prompts versionados que devam falhar cedo no CI

## O que fica no core

- `tests/test_pipeline.py` — orquestrador, agentes, integração com serviços mockados

## Como rodar

No Windows, se aparecer **`pytest` não é reconhecido**, use sempre **`python -m pytest`** (o `pytest` precisa estar no PATH ou o venv ativado).

```bash
# Só staging (rápido, pré-commit ou PR de conteúdo)
python -m pytest tests/staging/

# Por marcador
python -m pytest -m staging

# Suite completa (staging + core)
python -m pytest tests/
```

## Integração em CI sugerida

1. `python -m pytest tests/staging/` — falha rápida se `.md` ou parser quebrar  
2. `python -m pytest tests/test_pipeline.py` — valida o núcleo
