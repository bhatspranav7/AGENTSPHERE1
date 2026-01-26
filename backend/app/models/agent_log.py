from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String)
    action = Column(String)
    status = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
