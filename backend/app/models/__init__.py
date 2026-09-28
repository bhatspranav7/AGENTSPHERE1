"""All persistent state. Every agent action, plan version and supervisor
verdict is written here, so any execution can be audited or replayed."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db.session import Base


class ExecutionStatus:
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    CANCELLED = "cancelled"

    ACTIVE = (QUEUED, PLANNING, RUNNING)
    TERMINAL = (COMPLETED, FAILED, ABORTED, CANCELLED)


class ExecutionRun(Base):
    __tablename__ = "execution_runs"

    execution_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    objective: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=ExecutionStatus.QUEUED, index=True)
    phase: Mapped[str | None] = mapped_column(String(40))
    llm_mode: Mapped[str | None] = mapped_column(String(20))
    llm_model: Mapped[str | None] = mapped_column(String(80))
    chaos: Mapped[bool | None] = mapped_column(Boolean, default=False)
    chaos_mode: Mapped[str | None] = mapped_column(String(10))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    result: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    total_tokens: Mapped[int | None] = mapped_column(Integer, default=0)
    retries: Mapped[int | None] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class ExecutionPlan(Base):
    __tablename__ = "execution_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    version: Mapped[int] = mapped_column(Integer)
    plan_json: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str | None] = mapped_column(String(20))  # llm | simulated | fallback
    approved: Mapped[bool | None] = mapped_column(Boolean)
    validation_errors: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    step_id: Mapped[int] = mapped_column(Integer)
    agent_name: Mapped[str] = mapped_column(String(40))
    attempt: Mapped[int | None] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20))  # running | completed | rejected | failed
    objective: Mapped[str | None] = mapped_column(Text)
    input_payload: Mapped[dict | None] = mapped_column(JSON)
    output_payload: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SupervisorDecision(Base):
    __tablename__ = "supervisor_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    target: Mapped[str | None] = mapped_column(String(20))  # plan | step
    step_id: Mapped[int | None] = mapped_column(Integer)
    attempt: Mapped[int | None] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(20))  # APPROVE | RETRY | ABORT
    reason: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    decision_metadata: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExecutionEvent(Base):
    """Append-only event log: the timeline the UI streams and replays."""

    __tablename__ = "execution_events"
    __table_args__ = (Index("ix_execution_events_exec_id", "execution_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), default=datetime.utcnow)
