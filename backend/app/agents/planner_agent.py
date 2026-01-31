import uuid
from datetime import datetime

from backend.app.db.session import SessionLocal
from backend.app.models.execution import ExecutionRun
from backend.app.models.execution_plan import ExecutionPlan


class PlannerAgent:
    def create_plan(self, user_objective: str):
        db = SessionLocal()

        execution_id = uuid.uuid4()

        run = ExecutionRun(
            execution_id=execution_id,
            status="created",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(run)

        plan = {
            "steps": [
                {
                    "step_id": 1,
                    "agent": "ResearchAgent",
                    "task": f"Research objective: {user_objective}",
                },
                {
                    "step_id": 2,
                    "agent": "CodeAgent",
                    "task": "Generate initial implementation",
                },
            ]
        }

        plan_record = ExecutionPlan(
            execution_id=execution_id,
            version=1,
            plan_json=plan,
            validation_errors=None,
            created_at=datetime.utcnow(),
        )

        db.add(plan_record)
        db.commit()
        db.close()

        return execution_id, plan
