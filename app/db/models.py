"""Modelos ORM: execuções de avaliação e feedback pós-contratação."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Uma execução do pipeline: vaga, candidato, nota final, caminho do PDF e payload JSON opcional.
class EvaluationRun(Base):

    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    vaga: Mapped[str] = mapped_column(String(512))
    candidato: Mapped[str] = mapped_column(String(512))
    client_stem: Mapped[str | None] = mapped_column(String(512), nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_indication: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    feedbacks: Mapped[list[PerformanceFeedback]] = relationship(
        "PerformanceFeedback", back_populates="run", cascade="all, delete-orphan"
    )


# Feedback pós-contratação para calibrar nota vs performance na empresa.
class PerformanceFeedback(Base):

    __tablename__ = "performance_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    hired: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    company_performance_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # ex.: 1-5 ou 0-10
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[EvaluationRun] = relationship("EvaluationRun", back_populates="feedbacks")


# Scorecard estruturado (dimensoes 1-5, evidencias JSON) para ranking e API.
class ScorecardSnapshot(Base):

    __tablename__ = "scorecard_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    candidate_id: Mapped[str] = mapped_column(String(512), index=True)
    evaluator_id: Mapped[str] = mapped_column(String(512))
    role_slug: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    final_score: Mapped[float] = mapped_column(Float)
    recommendation: Mapped[str] = mapped_column(String(32))
    payload_json: Mapped[str] = mapped_column(Text)
