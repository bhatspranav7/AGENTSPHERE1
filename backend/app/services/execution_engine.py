from backend.app.db.session import SessionLocal
from backend.app.models.agent_execution import AgentExecution


class ExecutionEngine:
    def run(self, execution_id, plan: dict):
        """
        Executes a plan represented as a dict:
        {
            "steps": [
                {"step_id": 1, "agent": "ResearchAgent", "task": "..."},
                ...
            ]
        }
        """

        steps = plan.get("steps", [])

        db = SessionLocal()

        try:
            for step in steps:
                record = AgentExecution(
                    execution_id=execution_id,
                    step_id=step.get("step_id"),
                    agent_name=step.get("agent"),
                    output_payload={
                        "task": step.get("task"),
                        "result": "executed"
                    },
                    status="completed",
                )

                db.add(record)

            db.commit()

        finally:
            db.close()
