import uuid
import time
from sqlalchemy.orm import Session

from backend.app.models.execution_run import ExecutionRun, ExecutionStatus
from backend.app.core.logging import get_logger
from backend.app.core.exceptions import ExecutionError


class ExecutionService:
    def __init__(self, db: Session):
        self.db = db

    # -----------------------------
    # MOCK PRIMARY AGENT
    # -----------------------------
    def _primary_agent(self):
        # Simulate failure scenario
        raise Exception("Primary agent failed")

    # -----------------------------
    # MOCK FALLBACK AGENT
    # -----------------------------
    def _fallback_agent(self):
        # Simulate successful fallback
        return "Fallback agent executed successfully"

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

            # -----------------------------
            # RETRY + FALLBACK LOGIC
            # -----------------------------
            success = False

            for attempt in range(2):
                try:
                    logger.info(f"Primary agent attempt {attempt + 1}")
                    self._primary_agent()
                    success = True
                    break
                except Exception as e:
                    logger.warning(f"Primary agent failed on attempt {attempt + 1}: {str(e)}")
                    time.sleep(1)

            if not success:
                logger.info("Switching to fallback agent")
                try:
                    self._fallback_agent()
                    success = True
                    logger.info("Fallback agent executed successfully")
                except Exception as e:
                    logger.error(f"Fallback agent failed: {str(e)}")
                    success = False

            if not success:
                raise Exception("All agents failed")

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
    # LIST EXECUTIONS
    # -----------------------------
    def list_executions(self, limit: int = 10):
        return (
            self.db.query(ExecutionRun)
            .order_by(ExecutionRun.created_at.desc())
            .limit(limit)
            .all()
        )
    
