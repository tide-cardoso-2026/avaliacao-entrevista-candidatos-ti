# Perguntas técnicas — QA

> `COMMON` = qualidade e testes transversais. `AUTO`, `API`, `PERF`, `SEC` = foco. Ajuste o filtro à stack de testes da vaga.

## JUNIOR

[COMMON][JUNIOR][Diferença entre teste manual e automatizado][Manual explora e valida UX; automatizado repete verificações com regressão rápida]
[COMMON][JUNIOR][O que é caso de teste?][Pré-condição, passos, resultado esperado; base para rastreabilidade]
[COMMON][JUNIOR][O que é bug?][Comportamento que viola requisito ou expectativa acordada]
[AUTO][JUNIOR][Pirâmide de testes em linhas][Muitos unitários, menos integração, poucos E2E; custo e flakiness sobem no topo]
[AUTO][JUNIOR][O que é asserção?][Verificação que compara resultado real com esperado no teste]
[API][JUNIOR][Teste de contrato em APIs][Validar request/response contra schema ou pacto entre consumidor e provedor]

## PLENO

[COMMON][PLENO][Estratégia de regressão][Priorizar áreas de alto risco e mudanças recentes; smoke antes de suite completa]
[AUTO][PLENO][Testes flaky: causas][Race conditions, dados compartilhados, rede, relógio; isolar e estabilizar fixtures]
[AUTO][PLENO][Page Object Model][Encapsular seletores e ações de tela; reduz duplicação em E2E]
[AUTO][PLENO][Mocks vs stubs vs fakes][Mock verifica interações; stub retorna dados fixos; fake tem comportamento simplificado realista]
[API][PLENO][Testes de API sem UI][Validar status, corpo, headers, idempotência onde aplicável]
[CI][PLENO][Quality gate no pipeline][Testes obrigatórios antes de merge; relatório de cobertura com meta consciente do risco]

## SENIOR

[COMMON][SENIOR][Shift-left e shift-right][Prevenir defeitos cedo com revisão e testes; observar e testar em produção com feature flags e canários]
[COMMON][SENIOR][Risco vs cobertura de código][Cobertura alta não garante qualidade; focar em lógica crítica e combinações de risco]
[PERF][SENIOR][Testes de performance][Definir SLO, workload, ambientes isolados; não confundir latência pontual com percentis]
[SEC][SENIOR][Testes de segurança em QA][DAST em staging; revisão de dependências; validação de authZ em APIs]
[PROCESS][SENIOR][Definição de pronto para teste][Ambiente, dados, escopo e critérios de aceite claros evitam retrabalho]
[METRICS][SENIOR][Métricas de qualidade do processo][Defect escape rate, lead time para correção, taxa de reopen]
