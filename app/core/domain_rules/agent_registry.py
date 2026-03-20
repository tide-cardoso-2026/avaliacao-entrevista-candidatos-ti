"""Registro estático dos assistentes especialistas (nome, domínio, prompt e contexto permitido)."""

from __future__ import annotations

from pathlib import Path

from app.models.schemas import AgentDefinition


# Fornece a lista completa de `AgentDefinition` usada pelo seletor e pelo `AgentEngine`.
class AgentRegistry:

    # Raiz onde estão `prompts/assistants/*.md`.
    def __init__(self, *, prompts_root: str | Path = "prompts") -> None:
        self.prompts_root = Path(prompts_root)

    # Monta os perfis com caminhos de prompt, tier de modelo e KB em `data/technical-questions/`.
    def get_assistants(self) -> list[AgentDefinition]:
        generic_prompt_path = str(self.prompts_root / "assistants" / "generic_assistant.md")

        def assistant_prompt(filename: str) -> str:
            return str(self.prompts_root / "assistants" / filename)

        std = ["job_description_text", "cv_candidate_text", "interview_transcript_text"]

        return [
            AgentDefinition(
                agent_name="Tech Lead (TL)",
                domain="Arquitetura e Lideranca Tecnica",
                prompt_path=assistant_prompt("tech_lead_tl.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "arquitetura", "lideranca", "tech lead", "senior", "staff", "principal",
                ],
                assistant_model_tier="leadership",
                technical_kb_file=None,
            ),
            AgentDefinition(
                agent_name="Dev Backend",
                domain="Backend (APIs, performance, escalabilidade)",
                prompt_path=assistant_prompt("backend.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "backend", "api", "microservicos", "python", "java", "node", "go", "rust", "sql",
                ],
                assistant_model_tier="technical",
                technical_kb_file="backend.md",
            ),
            AgentDefinition(
                agent_name="Dev Frontend",
                domain="Frontend (UI, estado, acessibilidade)",
                prompt_path=assistant_prompt("frontend.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "frontend", "react", "angular", "vue", "javascript", "typescript", "css", "html", "ui",
                ],
                assistant_model_tier="technical",
                technical_kb_file="frontend.md",
            ),
            AgentDefinition(
                agent_name="QA",
                domain="Garantia da Qualidade (estrategia, testes, automacao)",
                prompt_path=assistant_prompt("qa.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "qa", "testes", "qualidade", "automacao", "selenium", "cypress", "testing",
                ],
                assistant_model_tier="technical",
                technical_kb_file="qa.md",
            ),
            AgentDefinition(
                agent_name="UX/UI",
                domain="Experiencia do Usuario e Interface",
                prompt_path=assistant_prompt("ux_ui.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "ux", "ui", "design", "figma", "usabilidade", "experiencia do usuario",
                ],
                assistant_model_tier="soft",
                technical_kb_file="ux_ui.md",
            ),
            AgentDefinition(
                agent_name="Agilista",
                domain="Processos Agile (ritmo, refinamento, cadencia)",
                prompt_path=assistant_prompt("agilista.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "agile", "kanban", "sprint", "agilista", "facilitacao", "processo", "ritual",
                ],
                assistant_model_tier="soft",
                technical_kb_file="agile_coach.md",
            ),
            AgentDefinition(
                agent_name="Scrum Master",
                domain="Scrum (time, impedimentos, rituais)",
                prompt_path=assistant_prompt("scrum_master.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "scrum master", "scrum", "daily", "sprint", "impedimento", "retrospectiva", "planning",
                ],
                assistant_model_tier="soft",
                technical_kb_file="scrum_master.md",
            ),
            AgentDefinition(
                agent_name="Agile Coach",
                domain="Coaching agile (mudanca, escala, metricas de fluxo)",
                prompt_path=assistant_prompt("agile_coach.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "agile coach", "coaching", "transformacao", "fluxo", "kanban", "escala",
                ],
                assistant_model_tier="soft",
                technical_kb_file="agile_coach.md",
            ),
            AgentDefinition(
                agent_name="Product Owner",
                domain="Visao de Produto (priorizacao, alinhamento)",
                prompt_path=assistant_prompt("product_owner.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "produto", "product", "backlog", "roadmap", "stakeholder", "priorizacao",
                ],
                assistant_model_tier="soft",
                technical_kb_file="product_owner.md",
            ),
            AgentDefinition(
                agent_name="Arquiteto DevOps (Azure/AWS)",
                domain="DevOps/Infra (CI/CD, cloud, observabilidade)",
                prompt_path=assistant_prompt("devops_cloud.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "devops", "cloud", "aws", "azure", "gcp", "kubernetes", "docker", "ci/cd", "infra", "sre",
                ],
                assistant_model_tier="technical",
                technical_kb_file="devops.md",
            ),
            AgentDefinition(
                agent_name="DevSecOps",
                domain="Seguranca no pipeline e supply chain",
                prompt_path=assistant_prompt("devsecops.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "devsecops", "seguranca", "sast", "dast", "sbom", "supply chain", "appsec",
                ],
                assistant_model_tier="technical",
                technical_kb_file="devsecops.md",
            ),
            AgentDefinition(
                agent_name="Arquiteto de Dados",
                domain="Dados (modelagem, pipelines, governanca)",
                prompt_path=assistant_prompt("data_architect.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "dados", "data", "modelagem", "dw", "data warehouse", "governanca", "lakehouse",
                ],
                assistant_model_tier="technical",
                technical_kb_file="data_engineer.md",
            ),
            AgentDefinition(
                agent_name="Engenheiro de IA",
                domain="IA aplicada (modelagem, MLOps, avaliacao)",
                prompt_path=assistant_prompt("ai_engineer.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "ia", "ai", "machine learning", "ml", "llm", "nlp", "deep learning", "mlops",
                ],
                assistant_model_tier="technical",
                technical_kb_file="ai_engineer.md",
            ),
            AgentDefinition(
                agent_name="Engenheiro de Dados",
                domain="Engenharia de Dados (ETL/ELT, qualidade)",
                prompt_path=assistant_prompt("data_engineer.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "data engineer", "etl", "elt", "pipeline", "spark", "airflow", "dbt", "engenharia de dados",
                ],
                assistant_model_tier="technical",
                technical_kb_file="data_engineer.md",
            ),
            AgentDefinition(
                agent_name="Cientista de Dados",
                domain="Ciencia de dados (estatistica, experimentos, modelagem)",
                prompt_path=assistant_prompt("data_scientist.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "cientista de dados", "data science", "estatistica", "experimento", "ab test",
                ],
                assistant_model_tier="technical",
                technical_kb_file="data_scientist.md",
            ),
            AgentDefinition(
                agent_name="Analista de Requisitos",
                domain="Requisitos (clarificacao, rastreabilidade, validacao)",
                prompt_path=assistant_prompt("requirements_analyst.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "requisitos", "analista", "business analyst", "documentacao", "especificacao",
                ],
                assistant_model_tier="soft",
                technical_kb_file="requirements_analyst.md",
            ),
            AgentDefinition(
                agent_name="Arquiteto de Solucao",
                domain="Arquitetura de solucao (negocio, integracao, ADR)",
                prompt_path=assistant_prompt("solution_architect.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "arquiteto de solucao", "solution architect", "integracao", "adr", "c4",
                ],
                assistant_model_tier="technical",
                technical_kb_file="solution_architect.md",
            ),
            AgentDefinition(
                agent_name="Arquiteto de Sistemas",
                domain="Arquitetura de sistemas (plataforma, confiabilidade, escala)",
                prompt_path=assistant_prompt("systems_architect.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "arquiteto de sistemas", "systems architect", "plataforma", "disponibilidade", "escala",
                ],
                assistant_model_tier="technical",
                technical_kb_file="systems_architect.md",
            ),
            AgentDefinition(
                agent_name="Engenheiro de Software",
                domain="Engenharia de software (codigo, design, entrega)",
                prompt_path=assistant_prompt("software_engineer.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "engenheiro de software", "software engineer", "desenvolvedor", "developer",
                ],
                assistant_model_tier="technical",
                technical_kb_file="software_engineer.md",
            ),
            AgentDefinition(
                agent_name="FullStack (Engenheiro de Software)",
                domain="Fullstack (entregas, integracoes, qualidade)",
                prompt_path=assistant_prompt("fullstack.md"),
                allowed_context_fields=std,
                relevance_keywords=[
                    "fullstack", "full-stack", "end-to-end", "integracao",
                ],
                assistant_model_tier="technical",
                technical_kb_file="fullstack.md",
            ),
            AgentDefinition(
                agent_name="Psicologa RH",
                domain="Comportamental (motivacao, adaptabilidade)",
                prompt_path=generic_prompt_path,
                allowed_context_fields=["cv_candidate_text", "interview_transcript_text"],
                relevance_keywords=[
                    "psicologia", "comportamental", "rh", "soft skills", "motivacao", "entrevista comportamental",
                ],
                assistant_model_tier="psych",
                technical_kb_file=None,
            ),
            AgentDefinition(
                agent_name="Psicologa Cultura empresa Taking",
                domain="Ajuste cultural (valores, contexto, colaboracao)",
                prompt_path=generic_prompt_path,
                allowed_context_fields=["cv_candidate_text", "interview_transcript_text"],
                relevance_keywords=[
                    "cultura", "valores", "taking", "fit cultural", "colaboracao", "alinhamento",
                ],
                assistant_model_tier="psych",
                technical_kb_file=None,
            ),
        ]
