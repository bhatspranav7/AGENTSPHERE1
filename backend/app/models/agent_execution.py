from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from backend.app.models.execution import Base


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(UUID(as_uuid=True), nullable=False)
    step_id = Column(Integer, nullable=False)
    agent_name = Column(String(64), nullable=False)
    input_payload = Column(JSONB, nullable=False)
    output_payload = Column(JSONB, nullable=False)
    status = Column(String(32), default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)
