from __future__ import annotations

from pathlib import Path

from app.models.schemas import AgentDefinition


class AgentRegistry:
    """
    Catalogo de agentes especialistas.
    """

    def __init__(self, *, prompts_root: str | Path = "prompts") -> None:
        self.prompts_root = Path(prompts_root)

    def get_assistants(self) -> list[AgentDefinition]:
        generic_prompt_path = str(self.prompts_root / "assistants" / "generic_assistant.md")
        p = lambda filename: str(self.prompts_root / "assistants" / filename)

        # MVP: mantemos os templates genericos, mas restringimos o contexto por dominio.
        return [
            AgentDefinition(
                agent_name="Tech Lead (TL)",
                domain="Arquitetura e Lideranca Tecnica",
                prompt_path=p("tech_lead_tl.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Dev Backend",
                domain="Backend (APIs, performance, escalabilidade)",
                prompt_path=p("backend.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Dev Frontend",
                domain="Frontend (UI, estado, acessibilidade)",
                prompt_path=p("frontend.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="QA",
                domain="Garantia da Qualidade (estrategia, testes, automacao)",
                prompt_path=p("qa.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="UX/UI",
                domain="Experiencia do Usuario e Interface",
                prompt_path=p("ux_ui.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Agilista",
                domain="Processos Agile (ritmo, refinamento, cadencia)",
                prompt_path=p("agilista.md"),
                allowed_context_fields=["cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Product Owner",
                domain="Visao de Produto (priorizacao, alinhamento)",
                prompt_path=p("product_owner.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Arquiteto DevOps (Azure/AWS)",
                domain="DevOps/Infra (CI/CD, cloud, observabilidade)",
                prompt_path=p("devops_cloud.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Arquiteto de Dados",
                domain="Dados (modelagem, pipelines, governanca)",
                prompt_path=p("data_architect.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Engenheiro de IA",
                domain="IA aplicada (modelagem, MLOps, avaliacao)",
                prompt_path=p("ai_engineer.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Engenheiro de Dados",
                domain="Engenharia de Dados (ETL/ELT, qualidade)",
                prompt_path=p("data_engineer.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Analista de Requisitos",
                domain="Requisitos (clarificacao, rastreabilidade, validacao)",
                prompt_path=p("requirements_analyst.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="FullStack (Engenheiro de Software)",
                domain="Fullstack (entregas, integrações, qualidade)",
                prompt_path=p("fullstack.md"),
                allowed_context_fields=["job_description_text", "cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Psicologa RH",
                domain="Comportamental (motivacao, adaptabilidade)",
                prompt_path=generic_prompt_path,
                allowed_context_fields=["cv_candidate_text", "interview_transcript_text"],
            ),
            AgentDefinition(
                agent_name="Psicologa Cultura empresa Taking",
                domain="Ajuste cultural (valores, contexto, colaboracao)",
                prompt_path=generic_prompt_path,
                allowed_context_fields=["cv_candidate_text", "interview_transcript_text"],
            ),
        ]

