# Instruções para assistentes — comparação com a base técnica

Use este arquivo **junto** com os `.md` de perguntas em `data/technical-questions/` (`backend.md`, `frontend.md`, `qa.md`, e os demais perfis listados no `README.md` da pasta). Ele resolve limitações de gabarito curto **sem** substituir julgamento humano.

## Como usar o gabarito por camadas

Cada pergunta pode ter, no último campo entre colchetes:

| Camada | Significado para o assistente |
|--------|-------------------------------|
| **MIN** | Critério mínimo: conceitos ou distinções que precisam aparecer na transcrição (equivalente semântico vale). |
| **STRONG** | Sinais de resposta **forte**: exemplo, trade-off, consequência prática, ou dois conceitos ligados corretamente. |
| **ANTI** | **Falso positivo**: citar buzzword sem explicar, confundir termos, ou resposta que soa correta mas está errada. |
| **BEHAV** | Comportamento esperado na **forma** da resposta (opcional): estrutura, admite limite do conhecimento, pede esclarecimento. |
| **FOLLOWUP** | Se a transcrição for ambígua, que **pergunta de esclarecimento** equivaleria a validar o conhecimento. |

Se a linha só tiver texto (sem `MIN:`), trate **todo o texto como MIN**.

### Regras (1) profundidade vs buzzword

- **Não** marque como “dominou” só porque o vocabulário do MIN aparece.
- Exija **STRONG** (quando existir na linha) ou, na ausência de STRONG, **dois elementos distintos** do MIN (ex.: definição + consequência ou exemplo) para nota alta.
- Se **ANTI** estiver preenchido e a resposta do candidato se encaixar, **penalize** a confiança da avaliação automática e cite o ANTI.

### Regras (2) sinais parciais

- Mapeie explicitamente: **cobre MIN** → baseline; **cobre STRONG** → acima do esperado; **cai em ANTI** → abaixo do esperado apesar de aparecer correto.

### Regras (3) comportamento (comunicação)

- Aplique **BEHAV** quando existir na linha.
- Se não existir BEHAV na linha, use o bloco **comportamental global** abaixo (leve).

### Comportamental global (leve)

- Resposta **estruturada** (contexto → resposta → exemplo) conta positivamente a partir de **pleno**.
- **Admitir** que não sabe algo específico é neutro ou levemente positivo se **não** inventar.
- Resposta **vaga** (uma frase genérica sem ancorar no problema) não satisfaz STRONG quando STRONG existir.

### Regras (4) cobertura de temas

- Se a linha for `COMMON`, aplique quando a conversa tocar no tema, mesmo que a stack não seja citada.
- Linhas com stack (`JAVA`, etc.) só entram na avaliação quando a stack da vaga ou o contexto da conversa corresponder.

### Regras (5) reduzir falso positivo por memorização

- **Exija** ligação entre conceitos (causa/efeito, ou “quando usar / quando não) **ou** exemplo concreto (mesmo breve) para classificar como “bem respondido”.
- Se só repetir definição de glossário sem aplicar ao cenário da pergunta, trate como **parcial** em relação ao STRONG (se houver) ou ao MIN.

## Saída sugerida na avaliação

Para cada tema relevante: `coberto|parcial|não coberto`, `evidência na transcrição`, `confiança (baixa/média/alta)`, `nota conceitual (se aplicável)`.
