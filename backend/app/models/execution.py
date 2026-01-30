from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from backend.app.db.base import Base


class ExecutionRun(Base):
    __tablename__ = "execution_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    status = Column(String(32), default="created")
    created_at = Column(DateTime, default=datetime.utcnow)


class ExecutionPlan(Base):
    __tablename__ = "execution_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(UUID(as_uuid=True), nullable=False)
    version = Column(Integer, nullable=False)
    plan_json = Column(JSONB, nullable=False)
    validation_errors = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SupervisorDecision(Base):
    __tablename__ = "supervisor_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(UUID(as_uuid=True), nullable=False)
    decision = Column(String(32), nullable=False)
    reason = Column(String(256), nullable=True)
    decision_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
