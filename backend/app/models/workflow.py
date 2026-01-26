from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from app.db.base import Base

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    user_request = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    steps = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
