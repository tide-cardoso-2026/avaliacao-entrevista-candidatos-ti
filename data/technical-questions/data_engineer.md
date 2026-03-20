# Perguntas técnicas — Engenheiro de dados

> Pipelines, armazenamento e qualidade. Tags `ETL`, `SQL`, `SPARK`, `ORCH`, `CLOUD`, `COMMON`.

## JUNIOR

[COMMON][JUNIOR][Diferença entre ETL e ELT][ETL transforma antes de carregar; ELT carrega bruto e transforma no destino com SQL escalável]
[SQL][JUNIOR][O que é chave surrogate?][Identificador artificial estável; útil quando chave natural muda ou é composta demais]
[SQL][JUNIOR][Diferença entre VIEW e tabela física][View é consulta salva; pode materializar para performance com custo de atualização]
[ETL][JUNIOR][O que é idempotência em job de carga?][Reexecutar produz o mesmo estado final sem duplicar fatos]

## PLENO

[SQL][PLENO][Modelagem estrela vs snowflake][Fato central com dimensões; snowflake normaliza dimensões; trade-off espaço vs joins]
[ORCH][PLENO][Airflow: DAG e operator][Grafo acíclico de tarefas; operators encapsulam trabalho; retries e SLA por task]
[SPARK][PLENO][DataFrame vs RDD em linhas][DataFrame com otimizador Catalyst; RDD mais controle imperativo e menos otimização declarativa]
[QUAL][PLENO][Great Expectations ou regras similares][Expectativas declarativas em colunas; relatórios e bloqueio de pipeline]
[CLOUD][PLENO][Data lake vs warehouse][Lake aceita variedade e schema-on-read; warehouse tende a schema forte e BI tradicional]

## SENIOR

[COMMON][SENIOR][CDC change data capture][Capturar mudanças na origem para reduzir batch full; ordenação e duplicatas]
[COMMON][SENIOR][Exactly-once em pipelines distribuídos][Idempotência na escrita; dedup; transações onde suportado]
[GOV][SENIOR][Linhagem de dados][Rastrear origem e transformações; impacto de mudança e conformidade]
[PERF][SENIOR][Particionamento e skew][Chave ruim concentra em poucos executores; sal observabilidade de shuffle]
[SEC][SENIOR][Segredos e PII em pipelines][Vault ou gestão de segredos; mascarar PII; segregação de ambientes]
[COST][SENIOR][Custo de cluster vs SLA][Auto scale com limites; armazenamento frio; compactação e formato colunar]
