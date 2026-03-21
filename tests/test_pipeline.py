"""Testes de integração do pipeline, parsing, localização de arquivos e mocks de LLM."""

import pytest
from reportlab.pdfgen import canvas

from app.core.exceptions import AmbiguousDocumentError, DocumentNotFoundError, UnsupportedFormatError
from app.core.orchestration.agent_engine import AgentEngine
from app.core.orchestration.middle_and_c_level import compute_weighted_score, detect_divergences
from app.core.protocols import LLMService
from app.models.executive_report import (
    CandidateHeader,
    ConsolidatedAnalysisBlock,
    DecisionBlock,
    DomainAnalysisBlock,
    ExecutiveEvaluationReport,
    FitBlock,
    HighlightsBlock,
    ScoreBreakdown,
)
from app.models.schemas import (
    AgentEvaluation,
    CTOFinalEvaluation,
    DocumentSet,
    FinalIndication,
    FinalRating,
)
from app.core.pipeline_events import (
    PipelineEventKind,
    ev_run_assistants,
    format_pipeline_event,
)
from app.pipeline.orchestrator import PipelineOrchestrator
from app.services.pipeline_ui_messages import humanize_message, ui_line
from app.services.parsing_service import ParsingService
from app.services.assistants_evaluation_pdf import write_assistants_evaluation_pdf
from app.services.report_generator import ReportGenerator
from app.utils.file_locator import FileLocator


# Deterministic mock that satisfies the LLMService protocol.
class MockLLMService:

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate_text(self, *, prompt: str, layer: str = "meta", max_tokens: int = 200) -> str:
        return "[mock humanizado]"

    def generate_json(
        self,
        *,
        prompt: str,
        context: str,
        layer: str = "assistants",
        assistant_model_tier: str | None = None,
        system_preamble: str | None = None,
    ) -> dict:
        self.calls.append(
            {
                "prompt": prompt,
                "context": context,
                "layer": layer,
                "assistant_model_tier": assistant_model_tier,
                "system_preamble": system_preamble,
            }
        )

        # Relatorio executivo (apos CTO) — deve vir antes de heuristica "final_score".
        if "EXECUTIVE_REPORT_JSON_V1" in prompt:
            return {
                "candidate": {"name": "Candidato", "role": "Vaga", "date": "2099-01-01"},
                "decision": {
                    "recommendation": "HIRE",
                    "level": "mid",
                    "score": 7.4,
                    "confidence": 0.78,
                },
                "highlights": {
                    "strengths": ["Forca A"],
                    "gaps": ["Gap B"],
                    "risks": ["Risco C"],
                },
                "summary": "Resumo executivo sintetico.",
                "score_breakdown": {
                    "technical": 7.4,
                    "architecture": 6.5,
                    "product": 6.0,
                    "communication": 5.5,
                },
                "consolidated_analysis": {
                    "strengths": ["Forca consolidada"],
                    "attention_points": ["Atencao 1"],
                    "risks": ["Risco consolidado"],
                },
                "domain_analysis": {
                    "backend": ["APIs REST solidas"],
                    "frontend": [],
                    "devops": [],
                    "security": ["JWT basico"],
                    "behavioral": ["Comunicacao clara"],
                },
                "conflicts": ["Divergencia exemplo"],
                "fit": {
                    "expected_level": "Senior",
                    "evaluated_level": "Pleno",
                    "gap": -1,
                    "recommendation": "Aprovar com ajuste de expectativa.",
                },
            }

        # Agent selector
        if "selected_agents" in prompt:
            return {
                "selected_agents": [
                    "Tech Lead (TL)", "Dev Backend", "Dev Frontend",
                    "QA", "FullStack (Engenheiro de Software)",
                    "Psicologa RH", "Psicologa Cultura empresa Taking",
                ],
                "rationale": {},
                "excluded_agents": {},
            }

        # CTO
        if "final_decision" in prompt or "final_score" in prompt:
            return {
                "agent": "delivery_manager",
                "final_decision": "APROVAR_COM_RESSALVAS",
                "final_score": 7.2,
                "executive_summary": "resumo executivo",
                "strategic_analysis": {"assessment": "Sinal estrategico moderado.", "evidence": ["ev1"]},
                "tactical_analysis": {"assessment": "", "evidence": []},
                "operational_analysis": {"assessment": "", "evidence": []},
                "technical_analysis": {},
                "behavioral_analysis": {},
                "client_benchmark": {"gap_level": "moderado", "notes": "notas benchmark"},
                "risks": [{"description": "risco exemplo", "impact": "medio", "probability": "media"}],
                "tradeoffs": ["Forte stack, pouca evidencia de lideranca"],
                "recommendations": ["recomendacao"],
                "confidence": 0.92,
            }

        # Middle management / deliberation
        if "conflicts_detected" in prompt or "follow_up_questions" in prompt or "calibration_notes" in prompt:
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

        # Follow-up round
        if "follow_up_answers" in prompt:
            return {
                "agent": "agente",
                "score": 7.5,
                "summary": "avaliacao revisada",
                "strengths": ["forca revisada"],
                "weaknesses": ["melhoria revisada"],
                "risks": ["risco"],
                "missing_evidence": [],
                "follow_up_answers": {},
                "confidence": 0.9,
            }

        # Default: assistant evaluation
        return {
            "agent": "agente",
            "score": 7.0,
            "summary": "recomendacao",
            "strengths": ["forca"],
            "weaknesses": ["melhoria"],
            "risks": ["risco"],
            "missing_evidence": [],
            "confidence": 0.85,
        }


# --- Protocol ---

def test_mock_satisfies_protocol():
    mock = MockLLMService()
    assert isinstance(mock, LLMService)


def test_pipeline_ui_line_and_humanize_log():
    text = ui_line("run_assistants", count=22)
    assert "22" in text
    assert "pareceres" in text.lower()
    h = humanize_message("Step 4/8: Running 22 specialist assistants")
    assert "22" in h
    assert "pareceres" in h.lower()


def test_pipeline_event_core_model():
    ev = ev_run_assistants(count=22)
    assert ev.kind == PipelineEventKind.RUN_ASSISTANTS
    assert ev.step == 4
    assert ev.payload["count"] == 22
    assert "22" in format_pipeline_event(ev)
    assert ev.model_dump()["kind"] == "run_assistants"


# --- Parsing ---

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
    with pytest.raises(UnsupportedFormatError):
        ps.load_text(weird)


# --- File locator ---

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


def test_file_locator_interview_fallback_when_single_file(tmp_path):
    """Sem nome a casar com o candidato: se existir só uma transcrição, usa-a."""
    base = tmp_path / "data"
    (base / "interviews").mkdir(parents=True)
    (base / "interviews" / "[TRANSCRICAO] Denis tecnico.docx").write_bytes(b"PK\x03\x04fake")
    locator = FileLocator(root_data_dir=base)
    p = locator.find_interview_transcript(stem_fragment="Douglas Lima", extensions=[".docx", ".txt", ".md", ".pdf"])
    assert p.name == "[TRANSCRICAO] Denis tecnico.docx"


def test_file_locator_interview_ambiguous_when_multiple_no_match(tmp_path):
    base = tmp_path / "data"
    (base / "interviews").mkdir(parents=True)
    (base / "interviews" / "a.docx").write_bytes(b"PK\x03\x04")
    (base / "interviews" / "b.docx").write_bytes(b"PK\x03\x04")
    locator = FileLocator(root_data_dir=base)
    with pytest.raises(AmbiguousDocumentError):
        locator.find_interview_transcript(stem_fragment="Zed", extensions=[".docx"])


# --- Confidence & Divergence (B, E) ---

def test_confidence_weighted_score():
    evals = [
        AgentEvaluation(agent_name="A", domain="d", score=9.0, confidence=0.9, strengths=[], improvements=[], risks=[], recommendation="r"),
        AgentEvaluation(agent_name="B", domain="d", score=3.0, confidence=0.3, strengths=[], improvements=[], risks=[], recommendation="r"),
    ]
    weighted = compute_weighted_score(evals)
    assert 7.0 < weighted < 9.0


def test_divergence_detection():
    evals = [
        AgentEvaluation(agent_name="A", domain="d", score=9.0, confidence=0.9, strengths=[], improvements=[], risks=[], recommendation="r"),
        AgentEvaluation(agent_name="B", domain="d", score=4.0, confidence=0.9, strengths=[], improvements=[], risks=[], recommendation="r"),
        AgentEvaluation(agent_name="C", domain="d", score=7.0, confidence=0.8, strengths=[], improvements=[], risks=[], recommendation="r"),
    ]
    flags = detect_divergences(evals)
    assert len(flags) >= 1
    assert any(f.score_spread >= 3.5 for f in flags)


def test_no_divergence_when_scores_close():
    evals = [
        AgentEvaluation(agent_name="A", domain="d", score=7.0, confidence=0.9, strengths=[], improvements=[], risks=[], recommendation="r"),
        AgentEvaluation(agent_name="B", domain="d", score=7.5, confidence=0.9, strengths=[], improvements=[], risks=[], recommendation="r"),
    ]
    flags = detect_divergences(evals)
    assert len(flags) == 0


def test_weighted_score_property():
    ev = AgentEvaluation(agent_name="A", domain="d", score=8.0, confidence=0.5, strengths=[], improvements=[], risks=[], recommendation="r")
    assert ev.weighted_score == 4.0


# --- Agent Engine ---

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
        assert 0.0 <= ev.confidence <= 1.0


def test_coerce_agent_payload_accepts_partial_llm_json():
    """LLM fraco pode devolver só score/confidence/missing_evidence sem agent/summary."""
    from app.core.domain_rules.agent_registry import AgentRegistry

    agent = AgentRegistry().get_assistants()[0]
    ev = AgentEngine._coerce_agent_payload(
        {"score": 6.0, "confidence": 0.4, "missing_evidence": ["Sem detalhe X no CV"]},
        agent=agent,
    )
    assert ev.agent_name == agent.agent_name
    assert ev.domain == agent.domain
    assert ev.score == 6.0
    assert ev.confidence == 0.4
    assert len(ev.missing_evidence) == 1


# --- Report Generator ---

def test_report_generator_creates_pdf(tmp_path):
    rg = ReportGenerator(output_dir=tmp_path / "outputs" / "reports")
    executive = ExecutiveEvaluationReport(
        candidate=CandidateHeader(name="Cand", role="Vaga X", date="2099-01-01"),
        decision=DecisionBlock(
            recommendation="HIRE",
            level="mid",
            score=7.2,
            confidence=0.85,
        ),
        highlights=HighlightsBlock(
            strengths=["S1"],
            gaps=["G1"],
            risks=["R1"],
        ),
        summary="Resumo.",
        score_breakdown=ScoreBreakdown(
            technical=7.0,
            architecture=7.0,
            product=7.0,
            communication=7.0,
        ),
        consolidated_analysis=ConsolidatedAnalysisBlock(
            strengths=["S1"],
            attention_points=["A1"],
            risks=["R1"],
        ),
        domain_analysis=DomainAnalysisBlock(backend=["B1"]),
        conflicts=[],
        fit=FitBlock(
            expected_level="Senior",
            evaluated_level="Pleno",
            gap=-1,
            recommendation="Ok.",
        ),
    )
    out = rg.generate_report(vaga="vaga", candidato="cand", executive=executive)
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


# --- Full Pipeline ---

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
        enable_agent_selection=False,
        enable_follow_up_round=False,
        enable_deliberation=False,
    )
    orchestrator.file_locator.root_data_dir = data_dir

    details = orchestrator.run_with_details(
        vaga="vaga", candidato="candidato", client=None, save_history=False, generate_report=True
    )
    assert details.report_path
    assert details.report_path.endswith(".pdf")
    assert details.assistants_pre_middle_pdf_path
    assert details.assistants_pre_middle_pdf_path.endswith(".pdf")


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
        enable_agent_selection=False,
        enable_follow_up_round=False,
        enable_deliberation=False,
    )
    orchestrator.file_locator.root_data_dir = data_dir

    details = orchestrator.run_with_details(
        vaga="vaga", candidato="candidato", client=None, generate_report=False, save_history=False
    )
    assert details.report_path is None
    assert details.assistants_pre_middle_pdf_path
    assert details.assistants_pre_middle_pdf_path.endswith(".pdf")
    assert details.cto_evaluation.score_final >= 0.0
    assert details.cto_evaluation.confidence > 0.0


def test_pipeline_with_all_features_enabled(tmp_path):
    data_dir = tmp_path / "data"
    (data_dir / "job_description").mkdir(parents=True)
    (data_dir / "candidates").mkdir(parents=True)
    (data_dir / "clients").mkdir(parents=True)
    (data_dir / "interviews").mkdir(parents=True)

    (data_dir / "job_description" / "job_backend_vaga.txt").write_text("JD: Python, APIs, backend, testes.", encoding="utf-8")
    (data_dir / "candidates" / "cv_candidato.txt").write_text("CV: experiencia em backend e APIs.", encoding="utf-8")
    (data_dir / "clients" / "client_vaga.txt").write_text("CV client: procura senioridade.", encoding="utf-8")
    (data_dir / "interviews" / "interview_candidato.md").write_text("Entrevista: respostas sobre arquitetura.", encoding="utf-8")

    orchestrator = PipelineOrchestrator(
        llm_service=MockLLMService(),
        report_generator=ReportGenerator(output_dir=tmp_path / "outputs" / "reports"),
        parsing_service=ParsingService(),
        enable_agent_selection=True,
        enable_follow_up_round=True,
        enable_deliberation=True,
    )
    orchestrator.file_locator.root_data_dir = data_dir

    details = orchestrator.run_with_details(
        vaga="vaga", candidato="candidato", client=None, generate_report=True, save_history=False
    )
    assert details.report_path is not None
    assert details.report_path.endswith(".pdf")
    assert details.assistants_pre_middle_pdf_path
    assert details.assistants_pre_middle_pdf_path.endswith(".pdf")
    assert details.cto_evaluation.score_final >= 0.0


def test_assistants_evaluation_pdf_pre_middle(tmp_path):
    ev = [
        AgentEvaluation(
            agent_name="A",
            domain="Backend",
            score=8.0,
            confidence=0.9,
            strengths=["s"],
            improvements=["i"],
            risks=["r"],
            recommendation="ok",
        ),
        AgentEvaluation(
            agent_name="B",
            domain="Arquitetura",
            score=3.0,
            confidence=0.8,
            strengths=["s2"],
            improvements=["i2"],
            risks=["r2"],
            recommendation="cuidado",
        ),
    ]
    out = write_assistants_evaluation_pdf(
        output_dir=tmp_path / "assistants_pre_middle",
        evaluations=ev,
        job_title="Vaga X",
        candidate_name="Cand Y",
        title="Test",
        footer_note="test",
        include_consolidation_summary=True,
    )
    assert out.is_file()
    assert out.stat().st_size > 0
    assert "assistants_pre_middle" in str(out)
