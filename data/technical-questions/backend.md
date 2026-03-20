# Perguntas técnicas — Backend

> `COMMON` = transversal (idempotência, observabilidade, etc.). Linhas com `JAVA` / `.NET` / `PYTHON` = específicas da stack. Filtrar pela stack da vaga evita ruído.

## JUNIOR

[JAVA][JUNIOR][Explique a diferença entre JVM, JRE e JDK][JVM executa bytecode; JRE = JVM + bibliotecas padrão; JDK = JRE + ferramentas (ex.: javac)]
[JAVA][JUNIOR][Qual a diferença entre == e .equals()?][== compara referência; .equals() compara valor quando bem sobrescrito (ex.: String)]
[JAVA][JUNIOR][O que é Garbage Collector?][Libera objetos não alcançáveis; o programador não desaloca manualmente]
[JAVA][JUNIOR][O que é uma Exception e como se trata?][Interrupção do fluxo; try/catch/finally; checked exigem declaração ou catch; unchecked em runtime]
[JAVA][JUNIOR][Diferença entre checked e unchecked exception][Checked obrigam tratamento em compile; unchecked (RuntimeException) não]
[JAVA][JUNIOR][O que significa String ser imutável?][Instância não muda; concatenação cria novo objeto]
[JAVA][JUNIOR][O que é encapsulamento?][Ocultar estado com modificadores e expor comportamento via API da classe]
[JAVA][JUNIOR][O que é herança e o que é composição?][Herança é relação é-um; composição é tem-um; preferir composição quando acoplamento for problema]
[JAVA][JUNIOR][O que é polimorfismo?][Mesma interface, implementações diferentes; override/overload]
[JAVA][JUNIOR][Diferença entre interface e classe abstrata][Interface: contrato; classe abstrata: pode ter estado e implementação parcial]

[.NET][JUNIOR][O que é .NET e o que é CLR?][.NET é a plataforma; CLR executa IL, GC e JIT]
[.NET][JUNIOR][Diferença entre .NET Framework e .NET (Core/modern)][Framework legado Windows; .NET atual é multiplataforma e unificado]
[.NET][JUNIOR][Diferença entre tipo valor e tipo referência][Valor no stack/inline; referência no heap; boxing/unboxing quando mistura]
[.NET][JUNIOR][O que é async/await em C#?][Sintaxe assíncrona sobre Task; libera thread enquanto aguarda I/O]
[.NET][JUNIOR][O que é LINQ?][Consultas sobre coleções com sintaxe fluente ou SQL-like]
[.NET][JUNIOR][O que é interface em C#?][Contrato explicitamente implementado por classes/structs]
[.NET][JUNIOR][Como funcionam exceptions em .NET?][Hierarquia Exception; try/catch/finally; não usar exceptions para fluxo normal]
[.NET][JUNIOR][O que é List<T> e quando usar em vez de array?][Coleção redimensionável; array tem tamanho fixo]
[.NET][JUNIOR][O que faz using com IDisposable?][Garante Dispose ao sair do escopo (try/finally sintético)]

[PYTHON][JUNIOR][O que é Python e como roda?][Interpretado; bytecode opcional; tipagem dinâmica]
[PYTHON][JUNIOR][Diferença entre lista e tupla][Lista mutável; tupla imutável; tupla como chave de dict se elementos forem hashable]
[PYTHON][JUNIOR][O que é dict?][Mapeamento chave-valor; ordem de inserção preservada (3.7+)]
[PYTHON][JUNIOR][O que é função de primeira classe?][Passar e retornar funções; base para decorators]
[PYTHON][JUNIOR][O que é lambda?][Função anônima de uma expressão; limitações vs def]
[PYTHON][JUNIOR][O que é list comprehension?][Construção concisa de listas com expressão e filtros]
[PYTHON][JUNIOR][O que é módulo e pacote?][Módulo = arquivo; pacote = diretório com __init__]
[PYTHON][JUNIOR][Como tratar erros?][try/except/else/finally; hierarquia BaseException/Exception]
[PYTHON][JUNIOR][O que é None?][Singleton do tipo NoneType; ausência de valor]
[PYTHON][JUNIOR][O que é venv ou virtualenv?][Ambiente isolado de dependências por projeto]

[GO][JUNIOR][O que é Go e para que serve?][Linguagem compilada, garbage collected, forte em concorrência com goroutines]
[GO][JUNIOR][O que é goroutine?][Função leve executada em paralelo com o scheduler do runtime]
[GO][JUNIOR][O que são channels?][Filas tipadas para comunicação entre goroutines; sincronização]
[GO][JUNIOR][O que é defer?][Adia execução até o retorno da função; ordem LIFO]
[GO][JUNIOR][Como tratar erros idiomático em Go?][if err != nil; erro como valor explícito]

[NODE][JUNIOR][O que é Node.js?][Runtime JavaScript no servidor baseado no motor V8]
[NODE][JUNIOR][O que é npm e package.json?][Gerenciador de pacotes; manifesto de dependências e scripts]
[NODE][JUNIOR][O que é require vs import?][CommonJS vs ESM; interoperabilidade gradual]
[NODE][JUNIOR][O que é event loop?][Loop que despacha I/O assíncrono e callbacks]

[KOTLIN][JUNIOR][O que é Kotlin na JVM?][Linguagem que compila para bytecode; interoperável com Java]
[KOTLIN][JUNIOR][O que é null safety?][Tipos T? e checagens para evitar NPE em tempo de compilação]
[KOTLIN][JUNIOR][Diferença entre val e var][val imutável; var mutável]

[RUST][JUNIOR][O que é ownership?][Cada valor tem um dono; liberação determinística sem GC]
[RUST][JUNIOR][O que é borrow checker?][Garante referências válidas em tempo de compilação]
[RUST][JUNIOR][O que é Result e Option?][Tipos para erro e ausência sem exceções obrigatórias]

[PHP][JUNIOR][O que é PHP e onde roda?][Linguagem server-side típica com Apache/Nginx+FPM]
[PHP][JUNIOR][O que é Composer?][Gerenciador de dependências PHP]

[RUBY][JUNIOR][O que é Ruby on Rails em uma frase?][Framework MVC com convenção sobre configuração]

[SQL][JUNIOR][O que é PRIMARY KEY?][Identificador único de linha; integridade referencial]
[SQL][JUNIOR][O que é FOREIGN KEY?][Referência a outra tabela; mantém consistência]
[SQL][JUNIOR][Diferença INNER e LEFT JOIN][INNER só linhas com match; LEFT mantém lado esquerdo com NULL]

## PLENO

[COMMON][PLENO][O que é injeção de dependências e que problema resolve?][Objetos recebem dependências de fora; facilita teste e troca de implementação]
[COMMON][PLENO][Como tratar erros de forma centralizada em uma API HTTP?][Handler global + mapeamento para status/corpo consistente; logging com correlação]
[COMMON][PLENO][Como async/await se relaciona com threads?][Await libera thread em I/O; não confundir com paralelismo CPU-bound]
[COMMON][PLENO][O que é JWT em APIs?][Token assinado; validar assinatura, expiração e claims em cada request stateless]
[COMMON][PLENO][O que é cache em APIs e quais invalidações existem?][TTL, eviction explícita, versionamento de chave; cuidado com consistência]
[COMMON][PLENO][Para que serve OpenAPI/Swagger?][Contrato da API, geração de cliente e documentação viva]
[COMMON][PLENO][Semântica de métodos HTTP em APIs REST][MIN: GET leitura; POST criação; PUT substituição total; PATCH parcial; DELETE remoção | STRONG: idempotência em GET/PUT/DELETE vs POST típico | ANTI: afirmar GET sempre seguro ignorando efeitos colaterais ou dados sensíveis em URL]
[COMMON][PLENO][O que é idempotência em HTTP][MIN: repetir a mesma requisição não amplia efeito além do esperado | STRONG: ligar a retries e erros de rede | ANTI: confundir com autenticação ou cache]
[COMMON][PLENO][Códigos HTTP 4xx vs 5xx][MIN: 4xx erro do cliente; 5xx erro do servidor | STRONG: exemplos 404/409/422 vs 503 | ANTI: devolver 200 com corpo de erro]
[COMMON][PLENO][Índice em banco relacional][MIN: estrutura que acelera busca; custo em escrita e armazenamento | STRONG: composto, covering, plano de consulta | ANTI: criar índice em tudo sem workload]
[COMMON][PLENO][Transação e ACID em linhas][MIN: atomicidade consistência isolamento durabilidade | STRONG: nível de isolamento e deadlock em linhas gerais | ANTI: prometer ACID distribuído sem nuance]
[COMMON][PLENO][Fila de mensagens vs tópico][MIN: fila um consumidor por mensagem típico; tópico fan-out | STRONG: DLQ retries ordenação por partição | ANTI: assumir entrega exatamente uma vez sem deduplicação]
[COMMON][PLENO][Consistência em mensageria][MIN: pelo menos uma entrega comum; deduplicação no consumidor | STRONG: idempotência outbox | ANTI: ignorar reprocessamento]

[JAVA][PLENO][Como funciona HashMap internamente?][Buckets por hash; colisão em lista/árvore; rehash quando fator de carga]
[JAVA][PLENO][Para que serve Stream API?][Pipeline declarativo: filter/map/reduce; pode ser lazy]
[JAVA][PLENO][Diferença entre map e flatMap em Optional/Stream][map: 1:1; flatMap: achata Optional/Stream aninhados]
[JAVA][PLENO][Para que serve Optional?][Representar ausência sem null; evitar NPE em encadeamentos]
[JAVA][PLENO][Como sincronizar acesso a estado compartilhado?][synchronized, locks explícitos, estruturas concurrent]
[JAVA][PLENO][O que é deadlock e como mitigar?][Ciclo de esperas por recursos; ordenar locks, timeout, evitar lock aninhado]
[JAVA][PLENO][Como DI funciona no Spring?][Container injeta beans por construtor; ciclo de vida gerenciado]
[JAVA][PLENO][Lazy vs Eager loading em JPA][Lazy: carga sob demanda; Eager: junta na consulta; cuidado com N+1]
[JAVA][PLENO][O que é DTO e por que usar na API?][Objeto estável do contrato HTTP; desacopla entidade de persistência]
[JAVA][PLENO][Como mapear exceções HTTP no Spring?][@ControllerAdvice + @ExceptionHandler por tipo de erro]

[.NET][PLENO][Como async/await compila em C#?][State machine sobre Task; sem thread extra por await de I/O]
[.NET][PLENO][Diferença entre Task e Thread][Task é trabalho assíncrono; Thread é recurso do SO; Task não implica thread 1:1]
[.NET][PLENO][O que é middleware no ASP.NET Core?][Pipeline encadeado; ordem importa para auth, roteamento, exceções]
[.NET][PLENO][O que é Entity Framework Core e tracking?][ORM; tracking detecta mudanças; AsNoTracking para leitura pesada]
[.NET][PLENO][Como implementar autenticação JWT típica?][Emitir token assinado; validar issuer/audience; refresh token se necessário]

[PYTHON][PLENO][O que é o GIL e o impacto?][Global Interpreter Lock: uma thread nativa executa bytecode por vez; CPU-bound paralelo usa multiprocessing]
[PYTHON][PLENO][Quando usar threading, asyncio ou multiprocessing?][I/O-bound: asyncio/threading; CPU-bound: multiprocessing ou native]
[PYTHON][PLENO][O que é asyncio e event loop?][Concorrência cooperativa; await em I/O não bloqueia loop]
[PYTHON][PLENO][O que é generator e yield?][Iteração preguiçosa; memória constante em pipelines]
[PYTHON][PLENO][O que são decorators?][Wrapper de função/classe para logging, cache, auth]
[PYTHON][PLENO][O que é context manager (with)?][Garante setup/teardown; protocolo __enter__/__exit__]
[PYTHON][PLENO][ORM típico e trade-offs][Abstração SQL; N+1 se não usar select/prefetch; migrações versionadas]
[PYTHON][PLENO][FastAPI em uma frase][ASGI; validação com Pydantic; OpenAPI automático]

[GO][PLENO][O que são interfaces em Go?][Conjunto de métodos satisfeitos implicitamente; polimorfismo estrutural]
[GO][PLENO][O que é context.Context?][Cancelamento, deadline e valores em cadeia de chamadas]
[GO][PLENO][Como evitar race conditions?][mutex, channels, ou -race no teste]
[GO][PLENO][O que é worker pool?][N goroutines consumindo jobs de um channel compartilhado]

[NODE][PLENO][O que é cluster module?][Distribui processos Node por núcleo de CPU]
[NODE][PLENO][O que é stream em Node?][Readable/Writable; backpressure para grandes volumes]
[NODE][PLENO][O que é middleware em Express?][Funções encadeadas req/res/next]
[NODE][PLENO][Event loop vs worker threads][Worker threads para CPU pesado; loop para I/O]

[KOTLIN][PLENO][Corrotinas em Kotlin][suspend; Dispatcher para threads; structured concurrency]
[KOTLIN][PLENO][Spring Boot com Kotlin][Mesmo ecossistema Spring; sintaxe mais concisa]

[RUST][PLENO][O que é Arc e Mutex?][Referência atômica compartilhada; exclusão mútua interior]
[RUST][PLENO][async/await em Rust][Executor; Future; runtime Tokio comum]

[PHP][PLENO][O que é OPcache?][Cache de bytecode PHP para reduzir parse em produção]
[PHP][PLENO][PSR e autoload][Padrões interoperáveis; Composer autoload PSR-4]

[ELIXIR][PLENO][O que é OTP e GenServer?][Biblioteca para processos tolerantes a falhas no BEAM]

[POSTGRES][PLENO][Índice B-tree vs GiST vs GIN][B-tree geral; GiST/GIN para full-text e JSON conforme caso]
[POSTGRES][PLENO][VACUUM e autovacuum][Recupera espaço; atualiza estatísticas; evita wraparound de txid]
[POSTGRES][PLENO][JSONB vs JSON][JSONB binário indexável; operadores e performance melhores]

[MONGODB][PLENO][Quando usar documento embutido vs referência][Embutir para dados lidos juntos; ref para reuso e tamanho]
[MONGODB][PLENO][O que é replica set?][Alta disponibilidade; eleição de primário; leituras opcionais em secundários]

[REDIS][PLENO][Estruturas Redis e uso][String, list, set, sorted set, hash; escolha pela operação]
[REDIS][PLENO][Persistência RDB vs AOF][Snapshot vs log de comandos; trade-off durabilidade vs disco]
[REDIS][PLENO][Eviction policies][LRU, LFU, TTL; risco de hot key]

[KAFKA][PLENO][Partição e chave de mensagem][Ordenação por partição; balanceamento com chave]
[KAFKA][PLENO][Consumer group][Cada partição consumida por um membro do grupo; rebalanceamento]
[KAFKA][PLENO][At-least-once e idempotência][Commits após processar; deduplicação no consumidor]

[GRPC][PLENO][gRPC vs REST][Protobuf binário; contrato forte; HTTP/2; streaming bidirecional]
[GRPC][PLENO][O que é protobuf?][IDL que gera stubs; serialização compacta]

[ELASTIC][PLENO][Índice shard e réplica][Shards para paralelismo; réplicas para busca e HA]
[ELASTIC][PLENO][Texto analisado vs keyword][Full-text com analyzer vs agregação/filtro exato]

[DOCKER][PLENO][Imagem vs container][Imagem é template; container é instância em execução]
[DOCKER][PLENO][Multi-stage build][Reduz tamanho final; só artefatos na última etapa]

[K8S][PLENO][Pod Deployment Service][Pod menor unidade; Deployment réplicas; Service descoberta e balanceamento]
[K8S][PLENO][Liveness e readiness probes][Reinício vs retirar do balanceamento de tráfego]

[AWS][PLENO][ALB vs NLB][ALB HTTP camada 7; NLB TCP performance e IPs estáticos]
[AWS][PLENO][SQS visão geral][Fila gerenciada; visibility timeout; DLQ]

## SENIOR

[COMMON][SENIOR][Como garantir idempotência em APIs?][Chave de idempotência, deduplicação, estado explícito; mesmo efeito com retry]
[COMMON][SENIOR][Lock pessimista vs otimista][Pessimista trava linha; otimista valida versão no commit; escolha por taxa de conflito]
[COMMON][SENIOR][Como compor resiliência entre serviços?][Retry com backoff, timeout, circuit breaker, bulkhead, fallback]
[COMMON][SENIOR][Trade-offs monolito vs microserviços][Deploy simples vs escala independente; complexidade operacional e de dados]
[COMMON][SENIOR][Como alinhar consistência eventual e negócio?][Eventos, sagas, compensação; definir limites aceitáveis de atraso]
[COMMON][SENIOR][Estratégia de cache distribuído][Redis/Memcached; TTL; invalidação por chave ou pub/sub; hot keys]
[COMMON][SENIOR][Observabilidade mínima em produção][Logs estruturados com trace id; métricas RED/USE; distributed tracing]
[COMMON][SENIOR][Como escalar APIs horizontalmente?][Stateless; sessão externa; filas para picos; autoscaling por métrica]
[COMMON][SENIOR][Como reduzir latência ponta a ponta?][Cache, query tuning, pooling, paralelismo seguro, CDN na borda]
[COMMON][SENIOR][Deploy sem downtime][Blue/green, canary, health checks antes de receber tráfego]
[COMMON][SENIOR][Alta disponibilidade][Múltiplas zonas; failover; eliminar SPOF; SLIs/SLOs]

[JAVA][SENIOR][Ferramentas típicas de resiliência no ecossistema Java][Resilience4j, Hystrix legado; integração com Spring Cloud]
[JAVA][SENIOR][Mensageria e consistência em Java][Kafka/Rabbit; transações locais + outbox/inbox; ordenação de partições]
[JAVA][SENIOR][Diagnóstico de memory leak e GC][Heap dump, MAT; GC logs; fugas por listeners estáticos ou caches sem limite]

[.NET][SENIOR][Resiliência idiomática em .NET][Polly: policies combinadas; integração com HttpClient factory]
[.NET][SENIOR][Escalar ASP.NET Core][Kestrel atrás de load balancer; Data Protection compartilhado se sessão; health endpoints]

[PYTHON][SENIOR][Mitigar GIL para workloads CPU-bound][Multiprocessing, C extensions, ou mover CPU para worker/service separado]
[PYTHON][SENIOR][Escalar serviços Python][Gunicorn/Uvicorn workers; processos para CPU; async para I/O; filas Celery/RQ quando cabe]

[GO][SENIOR][pprof e otimização][Profiling CPU/mem; benchmarks; alocações em hot path]
[GO][SENIOR][Graceful shutdown][Sinal + WaitGroup; drenar conexões antes de sair]

[NODE][SENIOR][Escala horizontal Node][Stateless; sticky session evitada; Redis para sessão se necessário]
[NODE][SENIOR][Memory leak típico][Closures segurando referências; listeners não removidos]

[KOTLIN][SENIOR][Corrotinas em produção][SupervisorJob; cancelamento em cascata; limitar paralelismo]

[RUST][SENIOR][Segurança em FFI][unsafe mínimo; UB; bindings C]

[POSTGRES][SENIOR][Isolamento e MVCC][Snapshots; phantom read conforme nível; vacuum longo]
[POSTGRES][SENIOR][Particionamento][Range/list/hash; pruning de partições em queries]

[MONGODB][SENIOR][Sharding][Distribui coleção; shard key imutável; hotspots se mal escolhida]

[REDIS][SENIOR][Cluster Redis][Hash slots; failover; cliente aware do cluster]

[KAFKA][SENIOR][Exactly-once end-to-end][Idempotência broker + transações + consumidor idempotente]
[KAFKA][SENIOR][Rebalanceamento e static membership][Evitar stop-the-world em deploys]

[GRPC][SENIOR][Deadline e cancellation][Propagar timeout; liberar recursos no servidor]

[ELASTIC][SENIOR][Cluster sizing e sharding][Evitar shards pequenos demais; forcemerge com cuidado]

[K8S][SENIOR][HPA e VPA][Métricas custom; limites vs requests; eviction]
[K8S][SENIOR][NetworkPolicy][Segmentação L3/L4 entre pods]

[AWS][SENIOR][Multi-AZ vs multi-region][HA na região vs DR; latência e consistência de dados]

[COMMON][SENIOR][API Gateway padrões][Auth rate limit roteamento; offload TLS; WAF na borda]
[COMMON][SENIOR][GraphQL trade-offs][Over-fetching reduzido; N+1 com DataLoader; complexidade de schema]
[COMMON][SENIOR][WebSockets vs SSE][Bidirecional vs servidor para cliente; reconexão e escala]
[COMMON][SENIOR][Rate limiting algoritmos][Token bucket; leaky bucket; sliding window]
[COMMON][SENIOR][OWASP API Security Top 10 visão][AuthZ quebrada; injeção; rate limit ausente]
[COMMON][SENIOR][Feature flags em backend][Toggle remoto; degradar sem deploy; cuidado com estado]
[COMMON][SENIOR][Dark launch e shadow traffic][Tráfego duplicado para validar sem impacto ao usuário]
[COMMON][SENIOR][Data residency e LGPD][Onde dados persistem; bases regionais; minimização]
[COMMON][SENIOR][SLA SLO SLI][Indicadores objetivos; orçamento de erro; alertas por burn rate]

> Stacks adicionais: GO, NODE, KOTLIN, RUST, PHP, RUBY, ELIXIR, POSTGRES, MONGODB, REDIS, KAFKA, GRPC, ELASTIC, DOCKER, K8S, AWS — filtrar por tag no prompt ou por vaga.
