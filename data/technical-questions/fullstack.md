# Perguntas técnicas — Full stack / Engenheiro de software (visão integrada)

> Mistura `FE`, `BE`, `API`, `COMMON`. Use para perfis que entregam ponta a ponta. Para especialização profunda, combine com `frontend.md` ou `backend.md`.

## JUNIOR

[COMMON][JUNIOR][O que significa full stack na prática?][Capacidade de trabalhar camada de apresentação e serviços com responsabilidade clara em cada]
[API][JUNIOR][Request HTTP básico][Método, URL, headers, corpo; resposta com status e corpo]
[BE][JUNIOR][O que é JSON?][Formato de troca de dados; tipos comuns string number boolean array object null]
[FE][JUNIOR][Por que separar front e back em repositórios ou camadas?][Deploy independente, times e contratos de API explícitos]

## PLENO

[COMMON][PLENO][Contrato de API entre times][OpenAPI, versionamento, compatibilidade retroativa e deprecação]
[COMMON][PLENO][Autenticação em fluxo com SPA][Onde guardar token; refresh; CSRF em cookies; implicações de XSS]
[BE][PLENO][Validação de entrada][Schema no servidor é obrigatório; cliente valida para UX não para segurança]
[FE][PLENO][Tratamento de erro na UI][Mensagens úteis, estados de carregamento e retry sem expor detalhes sensíveis]
[DATA][PLENO][ORM e SQL no mesmo projeto][ORM para produtividade; SQL pontual para relatórios e performance]
[DEVOPS][PLENO][O que o full stack costuma tocar em CI?][Build, testes, lint, artefato e deploy com variáveis por ambiente]

## SENIOR

[COMMON][SENIOR][Consistência eventual na UX][Mostrar estado intermediário; idempotência em ações; reconciliar com servidor]
[ARCH][SENIOR][Monólito modular vs microserviços para time pequeno][Complexidade operacional de microserviços sem necessidade é ANTI]
[SEC][SENIOR][Superfície de ataque em app full stack][Validação em todas as camadas; authZ no servidor; headers de segurança]
[PERF][SENIOR][Otimização ponta a ponta][Medir antes; gargalo pode ser DB, rede, bundle ou serialização]
[OBS][SENIOR][Correlação front e back][Trace ID da requisição do browser ao serviço para depurar incidentes]
