import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ExecutionRun(Base):
    __tablename__ = "execution_runs"

    execution_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_objective = Column(Text, nullable=False)
    source = Column(String(32), nullable=False)  # ollama | fallback
    status = Column(String(32), nullable=False)  # planned | approved | rejected
    created_at = Column(DateTime, default=datetime.utcnow)


class ExecutionPlan(Base):
    __tablename__ = "execution_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("execution_runs.execution_id"),
        nullable=False
    )
    version = Column(Integer, nullable=False)
    plan_json = Column(JSONB, nullable=False)
    validation_errors = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SupervisorDecision(Base):
    __tablename__ = "supervisor_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("execution_runs.execution_id"),
        nullable=False
    )
    decision = Column(String(32), nullable=False)  # approved | retry | rejected
    reason = Column(Text, nullable=False)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
