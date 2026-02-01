import uuid
from sqlalchemy.orm import Session

from backend.app.models.execution_run import ExecutionRun, ExecutionStatus
from backend.app.core.logging import get_logger
from backend.app.core.exceptions import ExecutionError


class ExecutionService:
    def __init__(self, db: Session):
        self.db = db

    # -----------------------------
    # START EXECUTION
    # -----------------------------
    def start_execution(self, user_objective: str) -> str:
        execution_id = uuid.uuid4()
        logger = get_logger(execution_id=str(execution_id))

        logger.info("Starting execution request")

        try:
            run = ExecutionRun(
                execution_id=execution_id,
                status=ExecutionStatus.created,
            )
            self.db.add(run)
            self.db.commit()
            logger.info("Execution created")

            run.status = ExecutionStatus.running
            self.db.commit()
            logger.info("Execution running")

            logger.info("Executing agents (placeholder)")

            run.status = ExecutionStatus.completed
            self.db.commit()
            logger.info("Execution completed successfully")

            return str(execution_id)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Execution failed: {str(e)}")

            run.status = ExecutionStatus.failed
            self.db.commit()

            raise ExecutionError("Execution failed internally")

    # -----------------------------
    # GET EXECUTION STATUS
    # -----------------------------
    def get_execution_status(self, execution_id: str):
        return (
            self.db.query(ExecutionRun)
            .filter(ExecutionRun.execution_id == execution_id)
            .first()
        )

    # -----------------------------
    # LIST EXECUTIONS (NEW)
    # -----------------------------
    def list_executions(self, limit: int = 10):
        return (
            self.db.query(ExecutionRun)
            .order_by(ExecutionRun.created_at.desc())
            .limit(limit)
            .all()
        )
