# Perguntas técnicas — Arquiteto de sistemas

> Profundidade em plataforma, integração, confiabilidade e escalabilidade. Tags `SYS`, `PERF`, `REL`, `COMMON`.

## JUNIOR

[SYS][JUNIOR][O que é acoplamento?][Grau em que mudança em um módulo força mudança em outro]
[SYS][JUNIOR][Latência vs throughput][Latência é tempo por operação; throughput é operações por unidade de tempo]
[COMMON][JUNIOR][SLA e SLO em linhas][SLA compromisso com cliente; SLO objetivo interno; erro orçamento liga os dois]

## PLENO

[REL][PLENO][Disponibilidade em noves][99.9 permite ~8,76h downtime/ano; cada nove exige engenharia e processo]
[PERF][PLENO][Gargalo][Limitar fator; otimizar sem medir é palpite; lei de Amdahl para paralelização]
[DATA][PLENO][Consistência em sistema distribuído][Transações locais vs sagas; compensação; idempotência]
[NET][PLENO][Balanceador de carga][Camada 4 vs 7; health check; sticky session quando necessário e seus custos]
[OBS][PLENO][Três pilares][Métricas logs traces; correlação entre eles para incident response]

## SENIOR

[SCALE][SENIOR][Escalabilidade horizontal vs vertical][Adicionar nós vs máquina maior; estado compartilhado é o inimigo comum]
[REL][SENIOR][Disaster recovery][RPO RTO; backup testado; runbook não é teoria em dia de incidente]
[SEC][SENIOR][Zero trust em infra][Verificar explicitamente; segmentação; não confiar na rede só porque é interna]
[SYS][SENIOR][Sistemas críticos e mudança][Janela de manutenção vs rolling deploy; feature flags e reversão rápida]
[COST][SENIOR][FinOps e arquitetura][Direito de tamanho de recurso; dados quentes e frios; revisão periódica de desperdício]
