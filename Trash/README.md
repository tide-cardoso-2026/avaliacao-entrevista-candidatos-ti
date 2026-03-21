# Trash

Arquivos **não referenciados** pelo runtime do sistema (CLI `app/main.py`, API, pipeline) foram movidos para cá para manter a raiz do repositório enxuta.

- Conteúdo pode ser apagado com segurança se você não precisar do histórico local.
- Não restaure nada para `app/` ou a raiz sem revisar dependências e testes.

## Conteúdo atual

| Item | Origem | Notas |
|------|--------|--------|
| `test_env.py` | raiz | Script de verificação de ambiente, não usado pelo pacote. |
| `scripts/` | `scripts/` | Utilitários one-off de formatação de código (não fazem parte do build). |
