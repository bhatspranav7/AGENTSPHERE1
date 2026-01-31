from sqlalchemy import Column, Integer, JSON, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from backend.app.db.engine import Base


class ExecutionPlan(Base):
    __tablename__ = "execution_plans"

    id = Column(Integer, primary_key=True)
    execution_id = Column(UUID(as_uuid=True), nullable=False)
    version = Column(Integer, nullable=False)
    plan_json = Column(JSON, nullable=False)
    validation_errors = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
