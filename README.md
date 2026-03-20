# EntrevistaTaking - Sistema de Avaliacao Inteligente de Candidatos

Pipeline multi-agente que gera laudos técnicos em PDF para avaliação de candidatos, usando LLMs para análise especializada em 3 camadas.

## Arquitetura

Board completo com diagrama detalhado: [`docs/board_arquitetura.md`](docs/board_arquitetura.md)

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

### Opções CLI

```bash
python -m app.main \
    --vaga "Engenheiro de Software"  \
    --candidato "Denis Palhares"     \
    --client "Marcelo Fonseca"       \
    --model "meta-llama/llama-3-8b-instruct" \
    --log-level DEBUG
```

### Docker

```bash
docker compose build
docker compose run entrevistataking --vaga "Engenheiro" --candidato "Denis"
```

## Desenvolvimento

```bash
# Instalar dependências de dev
pip install -r requirements.txt

# Testes
pytest -v

# Testes com cobertura
pytest --cov=app --cov-report=term-missing

# Linting
ruff check app/ tests/

# Type checking
mypy app/ --ignore-missing-imports
```

## Estrutura de Pastas

```
entrevistataking/
├── app/
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── exceptions.py          # Custom exception hierarchy
│   │   ├── protocols.py           # LLMService Protocol
│   │   ├── domain_rules/
│   │   │   └── agent_registry.py  # 15 specialist agent definitions
│   │   └── orchestration/
│   │       ├── agent_engine.py    # Layer 1 (parallel execution)
│   │       └── middle_and_c_level.py  # Layers 2 & 3
│   ├── models/
│   │   └── schemas.py             # Pydantic models (all contracts)
│   ├── pipeline/
│   │   └── orchestrator.py        # End-to-end pipeline coordination
│   ├── services/
│   │   ├── llm_service.py         # OpenAI/OpenRouter with retry
│   │   ├── parsing_service.py     # File parsers (txt/md/pdf/docx)
│   │   └── report_generator.py    # PDF generation
│   └── utils/
│       └── file_locator.py        # Data file resolution
├── prompts/                       # Prompt templates (Markdown)
│   ├── assistants/                # 13 specialist + 1 generic
│   ├── middle_management/         # 3 specialized + 1 generic
│   └── c_level/                   # CTO/Delivery Manager
├── data/                          # Input files (gitignored outputs)
├── tests/                         # pytest test suite
├── pyproject.toml                 # Project metadata & tool config
├── Dockerfile                     # Container image
├── docker-compose.yml             # Container orchestration
└── .github/workflows/ci.yml       # CI pipeline
```

## Convenções

- **Stem matching**: O sistema localiza arquivos por fragmento do nome (stem). Se `--candidato "Denis"`, busca `*Denis*` em `data/candidates/` e `data/interviews/`.
- **Ambiguity guard**: Se múltiplos arquivos casam com o mesmo fragmento, o sistema falha com erro explícito.
- **Logging**: Estruturado via `logging` module. Override com `--log-level DEBUG` ou `LOG_LEVEL=DEBUG` no `.env`.
