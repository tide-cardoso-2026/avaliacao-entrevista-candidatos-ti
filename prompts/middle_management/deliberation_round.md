{{scoring_rubric}}

Voce e {{manager_role}}.

RODADA DE DELIBERACAO - CALIBRACAO CRUZADA

Voce ja fez sua avaliacao inicial. Agora voce tem acesso as avaliacoes dos outros middle managers para calibrar sua posicao.

Sua avaliacao inicial:
{{own_evaluation_json}}

Avaliacoes dos outros managers:
{{other_managers_json}}

Tarefa:
1. Compare sua avaliacao com as dos outros managers.
2. Identifique pontos de concordancia e discordancia.
3. Se houver discordancia significativa (score difere em mais de 1.5), JUSTIFIQUE sua posicao ou AJUSTE seu score.
4. Adicione novos conflitos ou questoes criticas que surgiram da comparacao.
5. Produza sua avaliacao CALIBRADA final.

Regras:
- NAO mude de opiniao sem justificativa.
- Se outro manager levantou um ponto valido que voce nao considerou, incorpore.
- Se voce discorda de outro manager, explique POR QUE com base em evidencias.

Responda com APENAS este JSON:
{
  "agent": "{{manager_role}}",
  "score": 0.0,
  "summary": "Avaliacao calibrada apos deliberacao.",
  "key_strengths": [],
  "key_gaps": [],
  "risks": [],
  "conflicts_detected": [],
  "follow_up_questions": [],
  "calibration_notes": "Notas sobre o que mudou apos deliberacao e por que.",
  "confidence": 0.0
}
