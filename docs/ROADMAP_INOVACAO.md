# Roadmap de Inovação — EntrevistaTaking

Documento vivo que consolida decisões de produto, execução técnica, riscos e próximos passos.

---

## 1. Claude sem custo: resposta direta

| Pergunta | Resposta |
|----------|----------|
| **Dá para usar Claude “de graça” em produção?** | **Não de forma sustentável.** APIs (Anthropic direto ou OpenRouter) cobram por token. Créditos promocionais ou trials são temporários. |
| **O que é realista?** | Tratar LLM como **custo variável**: orçamento por execução, modelo por camada, monitoramento de uso. |
| **Estratégia recomendada** | **Roteamento por camada**: modelo econômico nos assistentes (15 chamadas), modelo intermediário no middle management, modelo premium (Claude / GPT-4 class) só no CTO e, se necessário, em 1–2 agentes críticos (ex.: Tech Lead). |

**Conclusão:** não há “Claude grátis” confiável para o produto; há **controle de custo** + **onde investir** na qualidade.

---

## 2. Prompt engineering + “usar LinkedIn”

### Objetivo
Aumentar **precisão, profundidade técnica e visão holística** sem depender de prompts genéricos.

### O que faz sentido
- **Matriz de competências por cargo** (backend, frontend, data, etc.): critérios explícitos, níveis de proficiência, exemplos de evidência no CV/transcrição.
- **Few-shot nos prompts** dos assistentes mais críticos: 1–2 exemplos de “boa avaliação” vs “avaliação incompleta”.
- **Enriquecimento com contexto de mercado** (sem scraping de perfis individuais): frameworks de mercado (Stack Overflow Survey, relatórios públicos, glossários internos da Taking).

### O que evitar (por enquanto)
- **Scraping automatizado de LinkedIn** para perfis de terceiros: risco de **ToS**, **LGPD**, **instabilidade** e **viés** (perfis incompletos).
- **Alternativa aceitável:** o candidato **autoriza** e cola um resumo profissional; ou uso de **dados já fornecidos** (CV + entrevista) como fonte única de verdade.

### Direção
> “LinkedIn como inspiração de competência” → transformar em **rubrics e bibliotecas de skills** versionadas no repositório, não em cópia de perfis.

---

## 3. Página web — “entrevista com agentes” (experiência de jornada)

### Visão
Interface onde o usuário (recrutador ou candidato em modo demo) **acompanha** a avaliação como uma “sala” com vários agentes, progresso lúdico, e resultado final na própria tela — com **download PDF** e histórico de sessão (sem banco de performance corporativo na primeira fase).

### Fluxo sugerido (MVP)
1. **Upload** ou colagem de JD, CV, transcrição (e opcional cliente).
2. **Sala de avaliação**: lista de agentes com status (pendente → em execução → concluído).
3. **Painel de síntese**: divergências, confiança, questões críticas (alinhado ao pipeline atual).
4. **Resultado**: laudo + PDF + link para download.

### Stack sugerida (MVP)
| Camada | Opção |
|--------|--------|
| API | **FastAPI** (Python, reutiliza pipeline) |
| Tempo real | **SSE** ou **WebSocket** para eventos de progresso |
| Frontend | **React** ou **Next.js** (SPA simples no primeiro corte) |
| Arquivos | PDF em `outputs/` + servir URL assinada ou download direto |
| Deploy | Docker (já existe base) + reverse proxy |

### Entregável incremental
- **v0:** API REST que dispara pipeline e retorna JSON + path do PDF.
- **v1:** UI com barra de progresso e lista de agentes.
- **v2:** animações “lúdicas”, temas, modo apresentação.

---

## 4. Proposta objetiva de execução (sem banco de performance por enquanto)

Escopo explícito: **não** implementar ainda “candidato X com nota 7.5 teve performance Y na empresa”.

### Fase A — Fundação (custo + qualidade)
1. **Variáveis de ambiente** por papel: `MODEL_ASSISTANTS`, `MODEL_MIDDLE`, `MODEL_CTO` (OpenRouter).
2. **Budget opcional** por execução (tokens estimados ou limite de chamadas premium).
3. **Few-shot** em 3 prompts críticos (ex.: `backend.md`, `tech_lead_tl.md`, CTO).

### Fase B — API
4. **FastAPI** com endpoint `POST /evaluate` (multipart ou JSON com paths).
5. **SSE** `GET /evaluate/{id}/stream` para eventos de agente.

### Fase C — Web
6. Frontend mínimo consumindo API + download PDF.

### Fora do escopo imediato
- Banco analítico de performance pós-contratação.
- Integração LinkedIn automatizada.

---

## 5. Análise final — melhorias esperadas e vulnerabilidades

### Melhorias esperadas (com as ideias acima)

| Área | Ganho esperado |
|------|----------------|
| **Qualidade** | Modelos maiores + roteamento no CTO reduzem decisões “rasas” e inconsistências. |
| **Consistência** | Rubrics + few-shot reduzem variância entre execuções. |
| **Experiência** | Web transmite valor ao cliente e facilita demos comerciais. |
| **Operação** | Budget e modelos por camada tornam custo previsível. |

### Vulnerabilidades e riscos (importante documentar)

| Risco | Descrição | Mitigação |
|-------|-----------|-----------|
| **Alucinação** | LLM inventa experiência ou projetos. | Manter anti-alucinação no CTO; exigir citação de evidência quando possível; revisão humana em decisões críticas. |
| **Viés** | Modelo e prompts podem favorecer certos perfis. | Auditoria periódica; diversidade nos exemplos few-shot; transparência no laudo. |
| **LGPD / dados** | CVs e transcrições são dados sensíveis. | Criptografia em trânsito, retenção mínima, política de exclusão, termos de uso na web. |
| **Segurança** | Upload de arquivos em API web. | Tipos MIME, tamanho máximo, scan básico, sandbox, não executar conteúdo de PDF. |
| **Custo** | Pico de uso com modelo premium em todos os agentes. | Roteamento + budget + cache de prompts (futuro). |
| **Dependência de provedor** | OpenRouter/Anthropic indisponíveis. | Retry (já existe), fallback de modelo, mensagem clara ao usuário. |
| **LinkedIn / scraping** | Bloqueio legal e técnico. | Não usar como fonte primária; preferir dados autorizados e rubrics internas. |

---

## 6. Próximos passos e roadmap de inovação

### Curto prazo (1–2 sprints)
- [ ] Implementar **modelos por camada** via `.env` + documentação.
- [ ] **Few-shot** nos 3 prompts críticos + revisão da rubrica.
- [ ] Esboço **OpenAPI** (FastAPI) com um job de avaliação.

### Médio prazo (1–2 meses)
- [ ] **UI** v1: upload + progresso + resultado + PDF.
- [ ] **SSE** para eventos em tempo real.
- [ ] Hardening: limites de upload, rate limit, logs estruturados.

### Longo prazo (inovação)
- [ ] **Biblioteca de competências** por cargo (versionada, auditável).
- [ ] **Modo “benchmark interno”**: comparar candidato com médias históricas (anônimas), **sem** banco de performance individual até existir processo de dados.
- [ ] **Integrações opcionais**: ATS, GitHub (com OAuth), não scraping de LinkedIn.
- [ ] **Observabilidade de qualidade**: painel com taxa de discordância entre agentes, confidence médio, tempo de execução.

### Roadmap visual (resumo)

```
[AGORA]  Roteamento modelo + few-shot + docs
    │
    ▼
[FASE B] FastAPI + job evaluate + SSE
    │
    ▼
[FASE C] Web jornada lúdica + PDF
    │
    ▼
[FUTURO] Banco performance + integrações + analytics
```

---

## Referência

- Pipeline atual: `app/pipeline/orchestrator.py`
- Rubrica: `prompts/shared/scoring_rubric.md`
- Configuração: `app/core/config.py`

*Última atualização: 2026-03-20 — alinhamento produto, engenharia e backlog técnico.*

---

## 7. Checklist técnico (pós-pipeline v2)

### Concluído (referência)
- [x] Managers em paralelo (`run_managers_parallel`) + merge + consolidador pré-CTO opcional (`ENABLE_PRE_CTO_CONSOLIDATOR`)
- [x] Deliberação condicional (`MIDDLE_DELIBERATION_SCORE_THRESHOLD`) com **own vs peers** por manager
- [x] Normalização pós-especialistas (`normalize_agent_evaluations`) e pós-follow-up
- [x] Pesos por agente logados (`compute_weighted_score_with_agent_weights`)
- [x] Heurística baseline CTO (`app/core/cto_heuristic.py`) + nota no laudo se divergir do LLM

### Ainda em aberto (próximas entregas)
- [ ] Endpoint `POST /evaluate` no FastAPI expondo o pipeline completo (JSON + opcional PDF) — hoje scorecard e CLI cobrem casos distintos
- [ ] SSE/WebSocket para progresso ao vivo na API
- [ ] Multi-tenant (`tenant_id`, `job_id`, `candidate_id`) no payload e no SQLite
- [ ] Fila (RQ/Celery) + Redis para jobs longos
- [ ] Cache por hash de input (economia de tokens)
- [ ] PDF executivo: seções dedicadas a trade-offs e riscos estruturados do CTO
- [ ] Usar `compute_weighted_score_with_agent_weights` na **seleção** ou **priorização** de agentes (não só log)

---

## 8. Roadmap — próximos passos (ordenado)

| Prioridade | Entrega | Notas |
|------------|---------|--------|
| P1 | API `POST /evaluate` + contrato estável | Base para UI e integrações |
| P2 | SSE de eventos (`pipeline_events`) | UX “sala de avaliação” |
| P3 | UI mínima (upload + resultado + PDF) | Demo comercial |
| P4 | Multi-tenant + isolamento de dados | SaaS |
| P5 | Fila + worker | Escalabilidade / timeouts |
| P6 | Biblioteca de competências versionada | Qualidade e auditoria |

Fluxo sugerido: **P1 → P2 → P3** para valor de produto; **P4–P6** quando houver tração ou requisitos enterprise.

