# Perguntas técnicas — Frontend

> `COMMON` = transversal. Tags `REACT`, `TS`, `CSS`, `WEB` = foco por tema. Filtrar pela stack da vaga reduz ruído.

## JUNIOR

[COMMON][JUNIOR][O que é o DOM?][Representação em árvore do HTML no navegador; APIs para ler e alterar nós]
[COMMON][JUNIOR][Diferença entre HTML e DOM][HTML é o documento; DOM é o modelo de objetos construído a partir dele]
[WEB][JUNIOR][O que é CORS?][Política do browser que restringe requests cross-origin sem cabeçalhos e permissões adequadas]
[WEB][JUNIOR][O que é Same-Origin Policy?][Isolamento de origem para cookies, DOM e dados entre sites]
[TS][JUNIOR][Para que serve TypeScript?][Tipagem estática opcional que compila para JavaScript e ajuda em refatoração e contratos]
[TS][JUNIOR][Diferença entre interface e type em TS][Ambos descrevem formas; interface pode ser estendida/merged de formas específicas; type é mais flexível para unions]
[CSS][JUNIOR][O que é box model?][content, padding, border, margin; box-sizing border-box inclui padding e border na largura]
[CSS][JUNIOR][Diferença entre margin e padding][padding é dentro da borda do elemento; margin é espaço externo entre elementos]
[REACT][JUNIOR][O que é JSX?][Sintaxe que parece HTML mas vira chamadas de createElement; className em vez de class]
[REACT][JUNIOR][O que são props?][Dados de fora para dentro do componente; fluxo principalmente unidirecional]
[REACT][JUNIOR][O que é estado local?][Dados que o componente controla e que disparam re-render ao mudar]
[A11Y][JUNIOR][O que é label associado a input?][Melhora leitores de tela e área clicável; usar htmlFor ou envolver o input]

## PLENO

[COMMON][PLENO][Virtual DOM vs atualização direta][Abstração que compara árvores e reduz manipulação imperativa; não é sinônimo de mais rápido em todo caso]
[COMMON][PLENO][Como evitar re-renders desnecessários][Memoização, keys estáveis, dividir estado, evitar objetos novos em props sem necessidade]
[REACT][PLENO][useEffect: dependências e limpeza][Array de deps define quando roda; cleanup para timers e subscriptions; evitar deps omitidas que causam bugs]
[REACT][PLENO][Estado global vs local][Local para UI efêmera; global para dados compartilhados entre rotas ou muitos filhos; custo de boilerplate e acoplamento]
[TS][PLENO][Generics em componentes][Props reutilizáveis com tipo parametrizado; inferência em funções de ordem superior]
[WEB][PLENO][Autenticação em SPA][Tokens em memória ou httpOnly cookies; refresh; XSS afeta o que está no JS]
[CSS][PLENO][Layout com Flexbox vs Grid][Flex para eixos e alinhamento em uma dimensão predominante; Grid para grades bidimensionais explícitas]
[PERF][PLENO][Code splitting e lazy routes][Carregar menos JS inicial; Suspense ou import dinâmico por rota]
[A11Y][PLENO][Foco visível e ordem de tab][Não remover outline sem substituto; tabindex só quando necessário]

## SENIOR

[COMMON][SENIOR][SSR vs CSR vs SSG vs ISR][Onde HTML nasce; SEO e TTFB vs interatividade; revalidação incremental em plataformas que suportam]
[COMMON][SENIOR][Micro-frontends trade-offs][Deploy independente vs consistência de UX, duplicação de libs e contratos de integração]
[REACT][SENIOR][Concurrent features e prioridade][Interrupção de renders; evitar starvation com disciplina de estado e suspense boundaries]
[WEB][SENIOR][Segurança front: XSS e CSP][Sanitizar HTML; CSP para reduzir injeção; confiar em frameworks sem checklist é ANTI]
[PERF][SENIOR][Web Vitals e campo vs lab][LCP INP CLS; medir usuários reais; lab não substitui RUM]
[ARCH_FE][SENIOR][Design system em escala][Tokens, acessibilidade, versionamento de pacotes, governança de contribuição]
