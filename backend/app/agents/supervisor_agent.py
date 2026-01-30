from datetime import datetime

from backend.app.db.session import SessionLocal
from backend.app.models.execution import SupervisorDecision
from backend.app.models.execution_plan import ExecutionPlanSchema


class SupervisorAgent:
    """
    Validates planner output, enforces schema,
    retries on failure, logs all decisions.
    """

    def __init__(self):
        self.db = SessionLocal()

    def review_plan(self, execution_id, plan_json, version, source="llm"):
        try:
            validated_plan = ExecutionPlanSchema.model_validate(plan_json)

            decision = SupervisorDecision(
                execution_id=execution_id,
                decision="approved",
                reason="Plan validated successfully",
                decision_metadata={
                    "source": source,
                    "version": version,
                },
                created_at=datetime.utcnow(),
            )

            self.db.add(decision)
            self.db.commit()

            return True, validated_plan, None

        except Exception as e:
            decision = SupervisorDecision(
                execution_id=execution_id,
                decision="retry",
                reason=str(e),
                decision_metadata={
                    "failure_type": "schema_error",
                    "version": version,
                },
                created_at=datetime.utcnow(),
            )

            self.db.add(decision)
            self.db.commit()

            retry_hint = (
                "Return ONLY valid JSON matching the required execution plan schema."
            )

            return False, None, retry_hint
