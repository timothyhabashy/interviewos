from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from interviewos.http.settings import database_url


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    clerk_subject: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("users.id"), nullable=True)
    guest_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="ready")
    engine_state: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TurnRow(Base):
    __tablename__ = "turns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), index=True)
    question_id: Mapped[str] = mapped_column(String(36))
    question_public: Mapped[dict] = mapped_column(JSON)
    answer: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuestionSecretRow(Base):
    __tablename__ = "question_secrets"

    question_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), index=True)
    correct_label: Mapped[str | None] = mapped_column(String(8), nullable=True)
    correct_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportRow(Base):
    __tablename__ = "reports"

    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def make_engine(url: str | None = None):
    target = url or database_url()
    kwargs: dict = {"future": True}
    if target.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in target or target in {"sqlite://", "sqlite+pysqlite://"}:
            kwargs["poolclass"] = StaticPool
    return create_engine(target, **kwargs)


def make_session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False, future=True)


def create_schema(engine) -> None:
    Base.metadata.create_all(engine)
