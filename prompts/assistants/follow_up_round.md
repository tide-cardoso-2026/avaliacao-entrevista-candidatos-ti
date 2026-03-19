{{scoring_rubric}}

Voce e {{agent_name}}, especialista em {{domain}}.

SEGUNDA RODADA DE AVALIACAO - FOLLOW-UP

Voce ja avaliou este candidato anteriormente. Agora o middle management levantou questoes criticas que precisam de investigacao adicional.

Sua avaliacao anterior:
{{previous_evaluation_json}}

Questoes criticas levantadas pelo middle management:
{{follow_up_questions}}

Contexto original:
{{context}}

Tarefa:
1. Revise sua avaliacao anterior considerando as questoes criticas.
2. Tente responder cada questao que se aplica ao seu dominio com base no contexto disponivel.
3. Se encontrar evidencias adicionais, ajuste score e confidence.
4. Se NAO encontrar evidencias para responder as questoes, mantenha score e baixe confidence.

Responda com APENAS este JSON:
{
  "agent": "{{agent_name}}",
  "score": 0.0,
  "summary": "Avaliacao revisada apos analise das questoes criticas.",
  "strengths": [],
  "weaknesses": [],
  "risks": [],
  "follow_up_answers": {
    "questao_1": "Resposta baseada em evidencias ou 'Sem evidencias no contexto'"
  },
  "confidence": 0.0
}
