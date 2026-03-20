# Perguntas técnicas — DevOps / SRE (infra e entrega)

> CI/CD, automação, nuvem e observabilidade. Tags `CI`, `K8S`, `OBS`, `CLOUD`, `COMMON`.

## JUNIOR

[COMMON][JUNIOR][O que é CI?][Integração contínua: merge frequente com build e testes automáticos]
[COMMON][JUNIOR][O que é CD?][Entrega ou deploy contínuo; pipeline leva mudança validada a produção com baixo atrito]
[DOCKER][JUNIOR][Imagem vs container][Imagem é template imutável; container é instância em execução]
[DOCKER][JUNIOR][Dockerfile em uma frase][Receita de camadas para construir imagem reproduzível]

## PLENO

[CI][PLENO][Pipeline típico][Lint test build scan artefato deploy; falhar cedo; cache de dependências]
[K8S][PLENO][Pod Deployment Service][Pod menor unidade; Deployment réplicas e rollout; Service descoberta e balanceamento]
[OBS][PLENO][Logs estruturados][JSON com campos estáveis; correlation id; evitar printf só em texto livre]
[IaC][PLENO][Infra as Code][Terraform ou Bicep; revisão de PR em infra; drift detection]
[REL][PLENO][Health check][Liveness vs readiness; não reiniciar à toa nem receber tráfego antes de pronto]

## SENIOR

[SRE][SENIOR][Error budget][SLO permite falhas; quando esgotado priorizar confiabilidade sobre features]
[SRE][SENIOR][Toil][Trabalho manual repetitivo que não escala; automatizar ou eliminar]
[SEC][SENIOR][Segredos em pipeline][Nunca no repositório; vault ou secret manager; rotação]
[SCALE][SENIOR][Cluster autoscaler vs HPA][Nós vs pods; dimensionar camada certa do problema]
[DR][SENIOR][Backup não testado é esperança][Restore periódico em ambiente isolado; documentar RPO alcançado]
