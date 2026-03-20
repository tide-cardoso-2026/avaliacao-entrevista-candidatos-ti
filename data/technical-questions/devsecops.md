# Perguntas técnicas — DevSecOps

> Segurança integrada ao ciclo de vida do software. Tags `SEC`, `SUPPLY`, `PIPE`, `COMMON`.

## JUNIOR

[SEC][JUNIOR][Shift-left em segurança][Encontrar vulnerabilidades cedo no ciclo; mais barato que em produção]
[SEC][JUNIOR][CVE em uma frase][Identificador público de vulnerabilidade conhecida em produto ou biblioteca]
[COMMON][JUNIOR][Princípio do menor privilégio][Contas e permissões só o necessário para a função]

## PLENO

[PIPE][PLENO][SAST e DAST][SAST analisa código estático; DAST testa app rodando; complementares]
[SUPPLY][PLENO][SBOM][Inventário de componentes de software; base para resposta a incidente de supply chain]
[SUPPLY][PLENO][Dependabot ou equivalente][PR automáticos para atualizar libs; revisar changelog e breaking changes]
[SEC][PLENO][Secrets scanning no repo][Bloquear commit com chave; histórico pode exigir rotação]
[CONT][PLENO][Imagem mínima e usuário não root][Reduz superfície; distroless ou alpine com cuidado de libc]

## SENIOR

[THREAT][SENIOR][STRIDE resumo][Spoofing tampering repudiation information disclosure denial of service elevation of privilege]
[GOV][SENIOR][Política de patch][SLA por severidade CVSS combinado com exposição real do ativo]
[ZERO][SENIOR][Confiança na pipeline][Assinar artefatos; verificar proveniência; política de admissão no cluster]
[INC][SENIOR][Resposta a vulnerabilidade crítica][Isolar comunicar remediar verificar; postmortem sem culpa]
[COMP][SENIOR][LGPD e segurança técnica][Minimização criptografia em trânsito e repouso; registro de acesso]
