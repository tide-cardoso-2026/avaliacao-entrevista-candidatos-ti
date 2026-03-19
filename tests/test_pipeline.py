import pytest

from app.core.exceptions import AmbiguousDocumentError, DocumentNotFoundError
from app.core.orchestration.agent_engine import AgentEngine
from app.core.protocols import LLMService
from app.models.schemas import (
    AgentEvaluation,
    CTOFinalEvaluation,
    DocumentSet,
    FinalIndication,
    FinalRating,
    MiddleManagementEvaluation,
)
from app.pipeline.orchestrator import PipelineOrchestrator
from app.services.parsing_service import ParsingService
from app.services.report_generator import ReportGenerator
from app.utils.file_locator import FileLocator

from reportlab.pdfgen import canvas


class MockLLMService:
    """Deterministic mock that satisfies the LLMService protocol."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate_json(self, *, prompt: str, context: str) -> dict:
        self.calls.append({"prompt": prompt, "context": context})

        if "final_decision" in prompt or "final_score" in prompt:
            return {
                "agent": "delivery_manager",
                "final_decision": "APROVAR_COM_RESSALVAS",
                "final_score": 7.2,
                "executive_summary": "resumo executivo",
                "strategic_analysis": {},
                "technical_analysis": {},
                "behavioral_analysis": {},
                "client_benchmark": {"gap_level": "moderado", "notes": "notas benchmark"},
                "risks": ["risco exemplo"],
                "recommendations": ["recomendacao"],
                "confidence": 0.92,
            }
        if "conflicts_detected" in prompt or "follow_up_questions" in prompt:
            return {
                "agent": "middle_manager",
                "score": 7.5,
                "summary": "analise consolidada",
                "key_strengths": [],
                "key_gaps": [],
                "risks": [],
                "conflicts_detected": [],
                "follow_up_questions": ["confirmar alinhamento com requisitos"],
                "confidence": 0.9,
            }

        return {
            "agent": "agente",
            "score": 7.0,
            "summary": "recomendacao",
            "strengths": ["forca"],
            "weaknesses": ["melhoria"],
            "risks": ["risco"],
            "confidence": 0.85,
        }


def test_mock_satisfies_protocol():
    mock = MockLLMService()
    assert isinstance(mock, LLMService)


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


def test_parsing_service_docx(tmp_path):
    ps = ParsingService()
    docx_path = tmp_path / "d.docx"

    from docx import Document as DocxDocument

    d = DocxDocument()
    d.add_paragraph("Docx content")
    d.save(str(docx_path))

    text = ps.load_text(docx_path)
    assert "Docx content" in text


def test_parsing_service_unsupported_format(tmp_path):
    ps = ParsingService()
    weird = tmp_path / "file.xyz"
    weird.write_text("nope", encoding="utf-8")
    with pytest.raises(Exception):
        ps.load_text(weird)


def test_file_locator_unique_and_ambiguity(tmp_path):
    base = tmp_path / "data"
    (base / "job_description").mkdir(parents=True)
    (base / "job_description" / "job_vaga_one.txt").write_text("x", encoding="utf-8")
    (base / "job_description" / "job_vaga_two.txt").write_text("y", encoding="utf-8")

    locator = FileLocator(root_data_dir=base)

    with pytest.raises(AmbiguousDocumentError):
        locator.find_by_stem(subdir="job_description", stem_fragment="vaga", extensions=[".txt", ".md", ".pdf"])

    (base / "job_description" / "job_other.txt").write_text("z", encoding="utf-8")
    unique = locator.find_by_stem(subdir="job_description", stem_fragment="one", extensions=[".txt", ".md", ".pdf"])
    assert unique.name.endswith("one.txt")


def test_file_locator_not_found(tmp_path):
    base = tmp_path / "data"
    (base / "job_description").mkdir(parents=True)
    locator = FileLocator(root_data_dir=base)

    with pytest.raises(DocumentNotFoundError):
        locator.find_by_stem(subdir="job_description", stem_fragment="nonexistent", extensions=[".txt"])


def test_agent_engine_executes_assistants_with_mock_llm():
    from app.core.domain_rules.agent_registry import AgentRegistry

    llm = MockLLMService()
    registry = AgentRegistry()
    agents = registry.get_assistants()

    documents = DocumentSet(
        job_description_text="JD",
        cv_candidate_text="CV candidate",
        cv_client_text="CV client",
        interview_transcript_text="Interview transcript",
    )

    engine = AgentEngine(llm_service=llm, max_workers=2)
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


def test_report_generator_creates_ranking_pdf(tmp_path):
    rg = ReportGenerator(output_dir=tmp_path / "outputs" / "reports")
    rows = [
        (
            "cand_a",
            CTOFinalEvaluation(
                final_rating=FinalRating.Senior,
                score_final=8.1,
                final_indication=FinalIndication.Aprovar,
                risks=[],
                observations="ok",
            ),
        ),
        (
            "cand_b",
            CTOFinalEvaluation(
                final_rating=FinalRating.Pleno,
                score_final=7.0,
                final_indication=FinalIndication.AprovarComRessalvas,
                risks=[],
                observations="ok",
            ),
        ),
    ]
    out = rg.generate_ranking_report(vaga="vaga", rankings=rows)
    assert out.endswith(".pdf")
    assert (tmp_path / "outputs" / "reports").exists()


def test_pipeline_single_candidate_mock_llm(tmp_path):
    data_dir = tmp_path / "data"
    (data_dir / "job_description").mkdir(parents=True)
    (data_dir / "candidates").mkdir(parents=True)
    (data_dir / "clients").mkdir(parents=True)
    (data_dir / "interviews").mkdir(parents=True)

    (data_dir / "job_description" / "job_backend_vaga.txt").write_text("JD: Python, APIs, testes.", encoding="utf-8")
    (data_dir / "candidates" / "cv_candidato.txt").write_text("CV: experiencia em backend.", encoding="utf-8")
    (data_dir / "clients" / "client_vaga.txt").write_text("CV client: procura senioridade moderada.", encoding="utf-8")
    (data_dir / "interviews" / "interview_candidato.md").write_text("Entrevista: respostas sobre arquitetura.", encoding="utf-8")

    orchestrator = PipelineOrchestrator(
        llm_service=MockLLMService(),
        report_generator=ReportGenerator(output_dir=tmp_path / "outputs" / "reports"),
        parsing_service=ParsingService(),
    )
    orchestrator.file_locator.root_data_dir = data_dir

    out_path = orchestrator.run(vaga="vaga", candidato="candidato", client=None)
    assert out_path.endswith(".pdf")


def test_pipeline_client_optional_when_clients_folder_empty(tmp_path):
    data_dir = tmp_path / "data"
    (data_dir / "job_description").mkdir(parents=True)
    (data_dir / "candidates").mkdir(parents=True)
    (data_dir / "clients").mkdir(parents=True)
    (data_dir / "interviews").mkdir(parents=True)

    (data_dir / "job_description" / "job_backend_vaga.txt").write_text("JD: Python.", encoding="utf-8")
    (data_dir / "candidates" / "cv_candidato.txt").write_text("CV: backend.", encoding="utf-8")
    (data_dir / "interviews" / "interview_candidato.md").write_text("Entrevista: respostas.", encoding="utf-8")

    orchestrator = PipelineOrchestrator(
        llm_service=MockLLMService(),
        report_generator=ReportGenerator(output_dir=tmp_path / "outputs" / "reports"),
        parsing_service=ParsingService(),
    )
    orchestrator.file_locator.root_data_dir = data_dir

    details = orchestrator.run_with_details(vaga="vaga", candidato="candidato", client=None, generate_report=False)
    assert details.report_path is None
    assert details.cto_evaluation.score_final >= 0.0
