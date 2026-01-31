from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from backend.app.db.engine import Base


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True)
    execution_id = Column(UUID(as_uuid=True), nullable=False)
    step_id = Column(Integer, nullable=False)
    agent_name = Column(String, nullable=False)
    output_payload = Column(JSON)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
