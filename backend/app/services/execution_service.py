import uuid
from sqlalchemy.orm import Session

from backend.app.models.execution_run import ExecutionRun, ExecutionStatus
from backend.app.core.logging import get_logger
from backend.app.core.exceptions import ExecutionError

# Import Agents
from backend.app.agents.planner_agent import PlannerAgent
from backend.app.agents.research_agent import ResearchAgent
from backend.app.agents.code_agent import CodeAgent
from backend.app.agents.automation_agent import AutomationAgent
from backend.app.agents.supervisor_agent import SupervisorAgent


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
            # Create execution record
            run = ExecutionRun(
                execution_id=execution_id,
                status=ExecutionStatus.created,
            )
            self.db.add(run)
            self.db.commit()

            logger.info("Execution created")

            # Update status to running
            run.status = ExecutionStatus.running
            self.db.commit()

            logger.info("Execution running")

            # -----------------------------
            # AGENT ORCHESTRATION
            # -----------------------------

            planner = PlannerAgent()
            researcher = ResearchAgent()
            coder = CodeAgent()
            automation = AutomationAgent()
            supervisor = SupervisorAgent()

            logger.info("Planner agent running")
            plan = planner.run(user_objective)

            logger.info("Research agent running")
            research = researcher.run(plan)

            logger.info("Code agent running")
            code = coder.run(research)

            logger.info("Automation agent running")
            result = automation.run(code)

            logger.info("Supervisor agent validating")
            supervisor.run(result)

            logger.info("All agents executed successfully")

            # -----------------------------
            # MARK EXECUTION COMPLETED
            # -----------------------------

            run.status = ExecutionStatus.completed
            self.db.commit()

            logger.info("Execution completed successfully")

            return str(execution_id)

        except Exception as e:
            self.db.rollback()

            logger.error(f"Execution failed: {str(e)}")

            # Mark failed if record exists
            try:
                run.status = ExecutionStatus.failed
                self.db.commit()
            except Exception:
                pass

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
