# Base de perguntas técnicas

Esta pasta guarda **perguntas técnicas de referência**, organizadas **por perfil** (ex.: backend, frontend, QA).

## Sincronização com o runtime

O `AgentRegistry` (`app/core/domain_rules/agent_registry.py`) mapeia cada assistente ao campo **`technical_kb_file`** (ex.: `backend.md`). O `AgentEngine` injeta automaticamente o conteúdo deste arquivo no contexto do prompt, respeitando `TECHNICAL_KB_MAX_CHARS` no `.env`.

## Regra de negócio

- Os assistentes usam estes arquivos como **base de conhecimento** na avaliação da entrevista.
- A avaliação pode considerar, entre outros pontos:
  - se **perguntas equivalentes** às listadas foram feitas;
  - se o candidato **respondeu** e com **clareza** (conceito correto, profundidade adequada ao nível).

Os arquivos **não substituem** o critério do entrevistador: servem de **checklist e vocabulário** para alinhar avaliação automática e humana.

## Formato canônico das linhas (obrigatório para geração automática)

Cada pergunta é **uma única linha** no padrão abaixo (definido em código em `app/core/technical_questions_format.py`):

```text
[STACK][NÍVEL][PERGUNTA][RESPOSTA_ESPERADA]
```

| Campo | Descrição |
|-------|-----------|
| **STACK** | Stack ou escopo: ex. `JAVA`, `PYTHON`, `.NET`, ou `COMMON` para itens **transversais** ao perfil (evita duplicar a mesma ideia em cada linguagem). |
| **NÍVEL** | Exatamente `JUNIOR`, `PLENO` ou `SENIOR` (alinhar com o subtítulo `## JUNIOR` etc. no mesmo arquivo). |
| **PERGUNTA** | Texto da pergunta. |
| **GABARITO** | Texto de comparação para assistentes. Pode ser **uma linha** (equivale a MIN) ou **camadas** (recomendado para tópicos críticos). |

**Gabarito em camadas** (opcional, separador ` | ` entre segmentos):

| Prefixo | Uso |
|---------|-----|
| `MIN:` | Mínimo aceitável (conceitos obrigatórios). |
| `STRONG:` | Sinais de resposta forte. |
| `ANTI:` | Anti-padrões / falso positivo (só citou termo, confundiu ideias). |
| `BEHAV:` | Expectativa de comportamento na forma da resposta. |
| `FOLLOWUP:` | Pergunta de esclarecimento se a transcrição for ambígua. |

Exemplo (sem `]` nos textos):

```text
[COMMON][PLENO][GET e POST em REST][MIN: GET não deve alterar estado; STRONG: POST criação e efeitos colaterais; ANTI: dizer que GET é sempre seguro sem falar de efeitos colaterais no servidor]
```

**Instruções para o assistente** (como aplicar MIN/STRONG/ANTI): ver `assistant_evaluation.md`.

**Restrição:** não use o caractere `]` dentro de PERGUNTA nem GABARITO (quebra o parser linha a linha).

**Markdown:** títulos de seção `## JUNIOR`, `## PLENO`, `## SENIOR` (com espaço após `##`).

## Convenção de arquivos

| Item | Convenção |
|------|-----------|
| Formato | Markdown (`.md`) |
| Um arquivo por perfil | Ver tabela abaixo; o assistente correspondente pode referenciar o mesmo nome em `prompts/assistants/`. |
| Stack base | Em entrevistas com stack definida, filtre por `STACK` no prompt ou no código; use `COMMON` para critérios que valem para qualquer stack do perfil. |

### Arquivos de perguntas por papel (KB)

| Arquivo | Foco |
|---------|------|
| `backend.md` | Backend e stacks de servidor |
| `frontend.md` | Web, frameworks de UI, performance e acessibilidade front |
| `qa.md` | Estratégia de testes, automação, qualidade |
| `fullstack.md` | Integração FE/BE e entrega ponta a ponta |
| `software_engineer.md` | Engenharia de software genérica (Git, design, processo) |
| `data_engineer.md` | Pipelines, DW/lake, orquestração, qualidade de dados |
| `ai_engineer.md` | ML/LLM em produção, MLOps, avaliação |
| `data_scientist.md` | Estatística, experimentação, modelagem analítica |
| `product_owner.md` | Produto, backlog, priorização, stakeholders |
| `scrum_master.md` | Scrum, eventos, impedimentos, métricas de time |
| `agile_coach.md` | Mudança organizacional, Kanban, métricas de fluxo |
| `requirements_analyst.md` | Requisitos, rastreabilidade, descoberta |
| `solution_architect.md` | Arquitetura de solução, integração, decisões (ADR) |
| `systems_architect.md` | Plataforma, confiabilidade, escalabilidade, observabilidade |
| `devops.md` | CI/CD, containers, nuvem, SRE |
| `devsecops.md` | Segurança no pipeline, supply chain, governança |
| `ux_ui.md` | Pesquisa, usabilidade, UI, inclusão |

**Não entram no contrato de linhas canônicas** (texto livre): `README.md`, `assistant_evaluation.md`.

### Papéis úteis que você pode acrescentar depois

Exemplos: **SRE** (já próximo de `devops.md`), **Engenheiro de plataforma**, **AppSec / segurança da aplicação**, **DBA / database reliability**, **Technical writer / DevRel**, **Product Manager** (diferente de PO em muitas empresas), **Engineering manager**, **Customer engineering / suporte técnico avançado**.

A pasta padrão é configurável via `TECHNICAL_QUESTIONS_DIR` no `.env` (ver `.env.example`).
