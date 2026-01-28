from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    attempt = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
