## Exemplos de avaliacao (few-shot) — siga o padrao

### Exemplo BOM (evidencia + score alinhado à rubrica)
Contexto: candidato descreveu 3 anos de APIs REST em microservicos, citou padroes de resiliencia e testes de integracao na entrevista.
```json
{
  "agent": "Dev Backend",
  "score": 7.5,
  "summary": "Experiencia pratica consistente em APIs e microservicos; evidencias claras na entrevista.",
  "strengths": ["Experiencia em APIs REST", "Menciona testes de integracao"],
  "weaknesses": ["Detalhes de observabilidade pouco explorados"],
  "risks": ["Escalabilidade sob carga extrema nao foi demonstrada"],
  "confidence": 0.85
}
```

### Exemplo RUIM (evitar)
- Score alto sem evidencia no contexto.
- Inventar tecnologias ou empresas nao mencionadas.
- Confidence alto quando o CV/transcricao nao cobre o dominio.

### Exemplo BOM (falta de evidencia)
Contexto: pouca informacao sobre o dominio na entrevista.
```json
{
  "agent": "Dev Backend",
  "score": 2.0,
  "summary": "Poucas evidencias no contexto para avaliar profundidade em backend.",
  "strengths": [],
  "weaknesses": ["Transcricao nao cobre detalhes tecnicos de APIs"],
  "risks": ["Nao e possivel validar experiencia real em producao"],
  "confidence": 0.35
}
```
