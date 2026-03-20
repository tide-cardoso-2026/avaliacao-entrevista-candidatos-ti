# EntrevistaTaking - Sistema de Avaliacao Inteligente de Candidatos

Pipeline multi-agente que gera laudos técnicos em PDF para avaliação de candidatos, usando LLMs para análise especializada em 3 camadas.

## Arquitetura

```
CLI (app/main.py)
    │
    ▼
PipelineOrchestrator
    │
    ├── Layer 1: 15 Specialist Agents (parallel via ThreadPool)
    │       Tech Lead, Backend, Frontend, QA, UX/UI, Agilista,
    │       Product Owner, DevOps, Data Architect, AI Engineer,
    │       Data Engineer, Requirements Analyst, FullStack,
    │       Psicóloga RH, Psicóloga Cultura
    │
    ├── Layer 2: Middle Management (3 managers or generic)
    │       Tech Manager, Product Manager, SRE Manager
    │
    └── Layer 3: C-Level / CTO (final decision)
            Score, Rating, Indication, Risks, Observations
```

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12+ |
| LLM API | OpenAI SDK via OpenRouter (compatible) |
| Validation | Pydantic v2 + pydantic-settings |
| PDF | ReportLab |
| Parsing | pypdf, python-docx |
| Resilience | tenacity (retry with exponential backoff) |
| Parallelism | concurrent.futures.ThreadPoolExecutor |
| Linting | Ruff |
| Type Checking | mypy |
| Testing | pytest + pytest-cov |
| CI/CD | GitHub Actions |
| Container | Docker |

## Roadmap e inovação

Estratégia de produto (Claude/custos, prompts, fases de execução, riscos e próximos passos): **[docs/ROADMAP_INOVACAO.md](docs/ROADMAP_INOVACAO.md)**.

## Quick Start

```bash
# 1. Clone e crie ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure variáveis de ambiente
cp .env.example .env
# Edite .env com sua OPENROUTER_API_KEY

# 4. Coloque os arquivos em data/
#    data/job_description/  - Job descriptions (.txt/.md/.pdf/.docx)
#    data/candidates/       - CVs dos candidatos
#    data/interviews/       - Transcrições de entrevistas
#    data/clients/          - (Opcional) Perfil do cliente/hiring manager

# 5. Execute
python -m app.main --vaga "Nome da Vaga" --candidato "Nome do Candidato"
```

- **Modelos por camada:** `.env` — `MODEL_ASSISTANTS`, `MODEL_ASSISTANTS_TECHNICAL` / `SOFT` / `LEADERSHIP` / `PSYCH` (por perfil de assistente), `MODEL_MIDDLE`, `MODEL_CTO`, `MODEL_META`. O default usa o mesmo ID em tudo (menor custo). Para laudo premium no CTO, defina `MODEL_CTO`; para roteamento de agentes mais estável, suba `MODEL_META`. `AGENT_ENGINE_MAX_WORKERS` e `TECHNICAL_KB_MAX_CHARS` controlam paralelismo e teto da KB injetada. Se aparecer **erro 402**, aumente créditos ou use modelo mais barato / `MAX_TOKENS=1024`.
- **Relatório final (PDF):** após o CTO, uma chamada LLM (`MODEL_CTO`, prompt `prompts/executive_report.md`) gera o contrato `ExecutiveEvaluationReport` (capa executiva, scorecard ponderado Técnico/Arquitetura/Produto/Comunicação, consolidação sem blocos por especialista, visão por domínio, fit de senioridade). O PDF omite JSON bruto e repetições do modelo antigo. Se a IA falhar, usa-se fallback determinístico.
- **API de scorecard (dimensões 1–5, evidências obrigatórias, ranking):** FastAPI em `app/api/main.py`. Subir com `uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000`. Opcional: defina `API_KEY` no `.env` e envie o header `X-API-Key` em todas as rotas exceto `GET /health`. Limite de taxa por IP: `API_RATE_LIMIT_PER_MINUTE` (slowapi). Inclui `POST /correlate-evaluations`, `GET /evaluators/{id}/stats`, golden self-check e `calibrationFlag`. Detalhes: `docs/AI_CANDIDATE_EVALUATION.md`.
- **Histórico:** execuções são gravadas em SQLite (`data/history.db`) salvo com `--no-save-history`.
- **LinkedIn:** `--linkedin-url` (com `PROXYCURL_API_KEY`) ou `--linkedin-file caminho.txt` com texto colado do perfil.

### Opções CLI

```bash
python -m app.main \
    --vaga "Engenheiro de Software"  \
    --candidato "Denis Palhares"     \
    --client "Marcelo Fonseca"       \
    --model "meta-llama/llama-3-8b-instruct" \
    --linkedin-file data/linkedin_candidato.txt \
    --log-level DEBUG
```

Flags opcionais: `--no-agent-selection`, `--no-follow-up`, `--no-deliberation`, `--no-save-history`, `--non-interactive` (falha se `data/` estiver vazio — adequado a CI/Docker).

### Docker

```bash
docker compose build
docker compose run entrevistataking --vaga "Engenheiro" --candidato "Denis"
```

## Desenvolvimento

- **Documentação no código:** cada módulo deve ter docstring inicial explicando o papel do arquivo. Para **funções e métodos**, use **comentários `#` na linha imediatamente acima** do `def` (não docstring dentro do corpo). **Métodos de classe:** o `#` deve usar a **mesma indentação** do `def`. Para **classes**, o comentário fica na linha acima de `class` (ou acima de `@dataclass` / decoradores, quando descrever o bloco).

```bash
# Instalar dependências de dev
pip install -r requirements.txt

# Testes (use `python -m pytest` se o comando `pytest` nao estiver no PATH — comum no Windows)
python -m pytest -v

# Testes com cobertura
python -m pytest --cov=app --cov-report=term-missing

# Linting
ruff check app/ tests/

# Type checking
mypy app/ --ignore-missing-imports
```

## Estrutura de Pastas

```
entrevistataking/
├── app/
│   ├── main.py                    # CLI (`entrevistataking`): dotenv + parse_cli_args + run_cli_session
│   ├── core/
│   │   ├── cli/                   # argparse, resolução de `data/`, runner, saída de terminal
│   │   ├── pipeline_events.py     # Eventos estruturados do pipeline + texto para UI
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── exceptions.py          # Custom exception hierarchy
│   │   ├── protocols.py           # LLMService Protocol
│   │   ├── domain_rules/
│   │   │   └── agent_registry.py  # 15 specialist agent definitions
│   │   └── orchestration/
│   │       ├── agent_engine.py    # Layer 1 (parallel execution)
│   │       └── middle_and_c_level.py  # Layers 2 & 3
│   ├── api/
│   │   └── main.py                # FastAPI (scorecard, rate limit, API key opcional)
│   ├── models/
│   │   ├── schemas.py             # Avaliações agentes / CTO / documentos
│   │   └── executive_report.py    # Contrato do laudo executivo (PDF)
│   ├── pipeline/
│   │   └── orchestrator.py        # End-to-end pipeline coordination
│   ├── services/
│   │   ├── llm_service.py         # OpenAI/OpenRouter with retry + log de tokens
│   │   ├── executive_report_service.py  # JSON executivo + normalização
│   │   ├── parsing_service.py     # File parsers (txt/md/pdf/docx)
│   │   └── report_generator.py    # PDF executivo + ranking
│   └── utils/
│       └── file_locator.py        # Data file resolution
├── prompts/                       # Prompt templates (Markdown)
│   ├── assistants/                # 13 specialist + 1 generic
│   ├── middle_management/         # 3 specialized + 1 generic
│   ├── c_level/                   # CTO/Delivery Manager
│   └── executive_report.md        # Laudo executivo consolidado (JSON)
├── data/                          # Input files (gitignored outputs)
├── docs/                          # Roadmap e documentação de produto
├── app/db/                        # SQLite: histórico e feedback
├── tests/                         # pytest test suite
├── Trash/                         # Arquivos não usados pelo sistema (só `README.md` versionado; ver lá)
├── pyproject.toml                 # Project metadata & tool config
├── Dockerfile                     # Container image
├── docker-compose.yml             # Container orchestration
└── .github/workflows/ci.yml       # CI pipeline
```

## Convenções

- **Stem matching**: O sistema localiza arquivos por fragmento do nome (stem). Se `--candidato "Denis"`, busca `*Denis*` em `data/candidates/` e `data/interviews/`.
- **Ambiguity guard**: Se múltiplos arquivos casam com o mesmo fragmento, o sistema falha com erro explícito.
- **Logging**: Estruturado via `logging` module. Override com `--log-level DEBUG` ou `LOG_LEVEL=DEBUG` no `.env`.
