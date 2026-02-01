import enum
from sqlalchemy import Column, String, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from backend.app.db.base import Base


class ExecutionStatus(str, enum.Enum):
    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"


class ExecutionRun(Base):
    __tablename__ = "execution_runs"

    execution_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    status = Column(
        Enum(ExecutionStatus, name="execution_status"),
        nullable=False,
        default=ExecutionStatus.created,
    )

    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
    )
