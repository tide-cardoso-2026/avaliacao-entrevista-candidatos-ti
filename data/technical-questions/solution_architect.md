# Perguntas técnicas — Arquiteto de solução

> Alinhamento negócio-tecnologia, desenho de solução ponta a ponta. Tags `ARCH`, `CLOUD`, `INTEG`, `COMMON`.

## JUNIOR

[ARCH][JUNIOR][O que é visão arquitetural em uma frase?][Decisões principais que são caras de mudar e como partes se conectam]
[COMMON][JUNIOR][Requisito não funcional exemplo][Disponibilidade latência throughput segurança conformidade custo]
[CLOUD][JUNIOR][IaaS PaaS SaaS em linhas][IaaS máquinas; PaaS runtime gerenciado; SaaS aplicação pronta]

## PLENO

[ARCH][PLENO][Diagramas C4][Contexto containers componentes código; nível de detalhe adequado ao público]
[INTEG][PLENO][Padrões de integração][Síncrono REST gRPC; assíncrono fila evento; escolha por acoplamento e consistência]
[CLOUD][PLENO][Multi-AZ][Alta disponibilidade na região; não é disaster recovery entre regiões sozinho]
[SEC][PLENO][Threat modeling básico][STRIDE ou similar; superfícies de ataque e mitigações documentadas]
[ADR][PLENO][Architecture Decision Record][Contexto decisão consequências; histórico para evitar repetir debates]

## SENIOR

[TRADE][SENIOR][CAP em contexto de negócio][Escolher consistência disponibilidade tolerância a partição conforme caso de uso]
[FIN][SENIOR][TCO e opex vs capex][Licença reserva spot; custo oculto de operação e suporte]
[VENDOR][SENIOR][Avaliação de fornecedor][Lock-in; roadmap; SLAs; saída e portabilidade de dados]
[GOV][SENIOR][Arquitetura corporativa e autonomia de squad][Padrões mínimos necessários; excesso de comitê mata fluxo]
[EVOL][SENIOR][Evolução de solução legada][Strangler; contratos estáveis; medir valor de cada etapa de modernização]
