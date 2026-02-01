import uuid
from sqlalchemy.orm import Session

from backend.app.models.execution_run import (
    ExecutionRun,
    ExecutionStatus,
)
from backend.app.core.logging import get_logger
from backend.app.core.exceptions import ExecutionError


class ExecutionService:
    def __init__(self, db: Session):
        self.db = db

    def start_execution(self, user_objective: str) -> str:
        """
        Starts a new execution run and manages its lifecycle.
        """

        # 1️⃣ Generate execution_id (UUID)
        execution_id = uuid.uuid4()

        logger = get_logger(execution_id=str(execution_id))

        try:
            # 2️⃣ Create execution row → CREATED
            run = ExecutionRun(
                execution_id=execution_id,
                status=ExecutionStatus.created,
            )
            self.db.add(run)
            self.db.commit()

            logger.info("Execution created")

            # 3️⃣ Mark as RUNNING
            run.status = ExecutionStatus.running
            self.db.commit()

            logger.info("Execution running")

            # -------------------------------------------------
            # 🔽 YOUR EXISTING EXECUTION LOGIC RUNS HERE
            # (agents, plans, etc — untouched)
            # -------------------------------------------------

            # 4️⃣ Mark as COMPLETED
            run.status = ExecutionStatus.completed
            self.db.commit()

            logger.info("Execution completed")

            return str(execution_id)

        except Exception as e:
            self.db.rollback()

            logger.error(f"Execution failed: {str(e)}")

            # 5️⃣ Mark as FAILED
            run.status = ExecutionStatus.failed
            self.db.commit()

            raise ExecutionError("Execution failed internally")
