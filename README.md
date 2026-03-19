# Sistema de Avaliacao Inteligente de Candidatos (MVP)

Este projeto gera um laudo tecnico em PDF para avaliacao de candidatos usando uma pipeline modular com multiplos agentes (assistentes especialistas -> middle management -> C-Level/CTO).

## Visao geral

O sistema:
1. Carrega inputs em `data/` (job_description, CVs e transcricao de entrevista)
2. Executa assistentes especialistas (cada um avaliando dentro do seu dominio)
3. Consolida resultados no middle management
4. Valida e fecha a decisao no C-Level (CTO), cruzando com o CV do cliente
5. Gera um PDF final em `outputs/reports/`

## Arquitetura

Principais modulos:
- `app/pipeline/orchestrator.py`: controla o fluxo e logs no terminal (ordem exigida)
- `app/core/domain_rules/agent_registry.py`: lista/configura os agentes e como cada um recebe contexto
- `app/core/orchestration/agent_engine.py`: executa a camada de assistentes usando prompts externos em `prompts/assistants/`
- `app/core/orchestration/middle_and_c_level.py`: consolida e finaliza (prompts em `prompts/middle_management/` e `prompts/c_level/`)
- `app/services/parsing_service.py`: parse de `.txt`, `.md` e `.pdf`
- `app/services/llm_service.py`: integracao com OpenAI retornando JSON estruturado
- `app/services/report_generator.py`: geracao do PDF com `reportlab`

## Estrutura de pastas

```text
project_root/
├─ app/
│  ├─ core/
│  │  ├─ domain_rules/
│  │  └─ orchestration/
│  ├─ pipeline/
│  └─ services/
├─ prompts/
│  ├─ assistants/
│  ├─ middle_management/
│  └─ c_level/
├─ data/
│  ├─ job_description/
│  ├─ candidates/
│  ├─ clients/
│  └─ interviews/
├─ outputs/
│  ├─ reports/
│  └─ logs/
└─ tests/
```

## Como rodar

1. Crie um ambiente virtual (recomendado):
   - `python -m venv venv`
   - `venv\Scripts\activate`
2. Instale dependencias:
   - `pip install -r requirements.txt`
3. Configure as variaveis de ambiente:
   - copie `.env.example` para `.env`
   - preencha `OPENAI_API_KEY`
4. Execute:
   - `python app/main.py --vaga <vaga> --candidato <candidato> --client <opcional>`

### Nome dos arquivos (stem convention)

O MVP localiza arquivos por `stem` (parte do nome do arquivo sem extensao), procurando o fragmento informado em:
- `data/job_description/*<vaga>*.txt|md|pdf`
- `data/candidates/*<candidato>*.txt|md|pdf`
- `data/interviews/*<candidato>*.txt|md|pdf`
- `data/clients/*<client_ou_vaga>*.txt|md|pdf` (se `--client` nao for informado, usa `--vaga`)

Se houver mais de um match para a categoria, o sistema falha com erro de ambiguidade para voce ajustar o nome.

## Exemplo de execucao

```bash
python app/main.py --vaga vaga --candidato candidato --client client
```

Exemplo de saida no terminal:
```text
[1/6] Carregando dados...
[2/6] Processando inputs...
[3/6] Executando Assistentes...
   - Tech Lead (TL) ✔
   - Dev Backend ✔
   ...
[4/6] Consolidando Middle Management...
[5/6] Avaliacao C-Level...
[6/6] Gerando relatorio final...
Relatorio gerado: outputs/reports/<vaga>_<candidato>_<YYMMDD_HHMM>.pdf
```

## Testes

```bash
pytest -q
```

