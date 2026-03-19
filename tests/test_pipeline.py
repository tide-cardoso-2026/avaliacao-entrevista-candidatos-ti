from app.pipeline.orchestrator import PipelineOrchestrator
from app.core.domain_rules.agent_registry import AgentRegistry
from app.core.orchestration.agent_engine import AgentEngine
from app.models.schemas import AgentEvaluation, CTOFinalEvaluation, FinalIndication, FinalRating, DocumentSet, MiddleManagementEvaluation
from app.services.parsing_service import ParsingService
from app.services.report_generator import ReportGenerator
from app.utils.file_locator import FileLocator

from reportlab.pdfgen import canvas


class MockLLMService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate_json(self, *, prompt: str, context: str) -> dict:
        self.calls.append({"prompt": prompt, "context": context})
        # Heuristica simples: decide qual schema esta pedindo com base em tokens do prompt.
        if '"final_rating"' in prompt or "final_rating" in prompt:
            return {
                "final_rating": "Junior",
                "score_final": 7.2,
                "final_indication": "Aprovar com ressalvas",
                "risks": ["(MVP) risco exemplo"],
                "observations": "(MVP) observacoes exemplo",
            }
        if '"score_consolidated"' in prompt or "score_consolidated" in prompt:
            return {
                "score_consolidated": 7.5,
                "conflicts": [],
                "critical_questions": ["(MVP) confirmar alinhamento com requisitos"],
                "analysis": "(MVP) analise consolidada",
            }

        # AgentEvaluation
        return {
            "agent_name": "(MVP) agente",
            "domain": "(MVP) dominio",
            "score": 7.0,
            "strengths": ["(MVP) forca"],
            "improvements": ["(MVP) melhoria"],
            "risks": ["(MVP) risco"],
            "recommendation": "(MVP) recomendacao",
        }


def test_parsing_service_txt_and_md(tmp_path):
    ps = ParsingService()
    txt = tmp_path / "a.txt"
    md = tmp_path / "b.md"
    txt.write_text("Hello txt", encoding="utf-8")
    md.write_text("# Hello md\n\nSecond line", encoding="utf-8")
    assert ps.load_text(txt) == "Hello txt"
    assert "Hello md" in ps.load_text(md)


def test_parsing_service_pdf(tmp_path):
    ps = ParsingService()
    pdf_path = tmp_path / "c.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(50, 800, "PDF content")
    c.showPage()
    c.save()
    text = ps.load_text(pdf_path)
    assert "PDF content" in text


def test_file_locator_unique_and_ambiguity(tmp_path):
    base = tmp_path / "data"
    (base / "job_description").mkdir(parents=True)
    (base / "job_description" / "job_vaga_one.txt").write_text("x", encoding="utf-8")
    (base / "job_description" / "job_vaga_two.txt").write_text("y", encoding="utf-8")

    locator = FileLocator(root_data_dir=base)
    # Ambiguidade
    try:
        locator.find_by_stem(subdir="job_description", stem_fragment="vaga", extensions=[".txt", ".md", ".pdf"])
        assert False, "Expected ambiguity error"
    except ValueError as e:
        assert "Ambiguidade" in str(e)

    # Unico
    (base / "job_description" / "job_other.txt").write_text("z", encoding="utf-8")
    unique = locator.find_by_stem(subdir="job_description", stem_fragment="one", extensions=[".txt", ".md", ".pdf"])
    assert unique.name.endswith("one.txt")


def test_agent_engine_executes_assistants_with_mock_llm(tmp_path):
    llm = MockLLMService()
    registry = AgentRegistry()
    agents = registry.get_assistants()

    documents = DocumentSet(
        job_description_text="JD",
        cv_candidate_text="CV candidate",
        cv_client_text="CV client",
        interview_transcript_text="Interview transcript",
    )

    engine = AgentEngine(llm_service=llm)
    evaluations = engine.run_assistants(agents=agents[:3], documents=documents)
    assert len(evaluations) == 3
    for ev in evaluations:
        assert isinstance(ev, AgentEvaluation)
        assert 0.0 <= ev.score <= 10.0


def test_report_generator_creates_pdf(tmp_path):
    rg = ReportGenerator(output_dir=tmp_path / "outputs" / "reports")
    mm = MiddleManagementEvaluation(
        score_consolidated=7.5,
        conflicts=[],
        critical_questions=["Q1"],
        analysis="Analise",
    )
    cto = CTOFinalEvaluation(
        final_rating=FinalRating.Junior,
        score_final=7.2,
        final_indication=FinalIndication.AprovarComRessalvas,
        risks=["risk1"],
        observations="obs",
    )
    assistants = [
        AgentEvaluation(
            agent_name="Dev Backend",
            domain="Backend",
            score=7.0,
            strengths=["s"],
            improvements=["i"],
            risks=["r"],
            recommendation="rec",
        )
    ]
    out = rg.generate_report(
        vaga="vaga",
        candidato="cand",
        assistant_evaluations=assistants,
        middle_management_evaluation=mm,
        cto_evaluation=cto,
    )
    assert out.endswith(".pdf")
    assert (tmp_path / "outputs" / "reports").exists()

def test_pipeline_single_candidate_mock_llm(tmp_path):
    # Cria fixture de inputs para a pipeline.
    data_dir = tmp_path / "data"
    (data_dir / "job_description").mkdir(parents=True)
    (data_dir / "candidates").mkdir(parents=True)
    (data_dir / "clients").mkdir(parents=True)
    (data_dir / "interviews").mkdir(parents=True)

    (data_dir / "job_description" / "job_backend_vaga.txt").write_text("JD: Python, APIs, testes.", encoding="utf-8")
    (data_dir / "candidates" / "cv_candidato.txt").write_text("CV: experiencia em backend.", encoding="utf-8")
    (data_dir / "clients" / "client_vaga.txt").write_text("CV client: procura senioridade moderada.", encoding="utf-8")
    (data_dir / "interviews" / "interview_candidato.md").write_text("Entrevista: respostas sobre arquitetura e testes.", encoding="utf-8")

    orchestrator = PipelineOrchestrator(
        llm_service=MockLLMService(),
        report_generator=ReportGenerator(output_dir=tmp_path / "outputs" / "reports"),
        parsing_service=ParsingService(),
    )
    # Sobrescreve locator para usar tmp_path.
    orchestrator.file_locator.root_data_dir = data_dir  # type: ignore[attr-defined]

    out_path = orchestrator.run(vaga="vaga", candidato="candidato", client=None)
    assert out_path.endswith(".pdf")

