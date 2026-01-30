import json
import logging
from typing import Optional, Tuple

from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.models.execution_plan import ExecutionPlan as PlanSchema
from backend.app.models.execution import (
    ExecutionRun,
    ExecutionPlan,
    SupervisorDecision,
)
from backend.app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """
    Supervisor is the final authority.
    - Validates planner output
    - Decides retry / approve / reject
    - Persists all decisions and versions
    """

    MAX_RETRIES = 2

    def __init__(self):
        self.db: Session = SessionLocal()

    # ------------------------
    # PUBLIC ENTRY POINT
    # ------------------------
    def review_plan(
        self,
        execution_id,
        raw_plan_output: str,
        source: str,
        attempt: int,
    ) -> Tuple[bool, Optional[PlanSchema]]:
        """
        Returns:
        - approved (bool)
        - validated ExecutionPlan (or None)
        """

        plan_json, error = self._parse_json(raw_plan_output)

        version = self._get_next_version(execution_id)

        if error:
            self._persist_plan(
                execution_id,
                version,
                None,
                {"error": error},
            )

            return self._handle_failure(
                execution_id,
                attempt,
                reason="Invalid JSON from planner",
                error=error,
            )

        # Schema validation
        try:
            validated_plan = PlanSchema.model_validate(plan_json)
        except ValidationError as ve:
            self._persist_plan(
                execution_id,
                version,
                plan_json,
                json.loads(ve.json()),
            )

            return self._handle_failure(
                execution_id,
                attempt,
                reason="Schema validation failed",
                error=str(ve),
            )

        # SUCCESS PATH
        self._persist_plan(
            execution_id,
            version,
            plan_json,
            None,
        )

        self._persist_decision(
            execution_id,
            decision="approved",
            reason="Plan validated successfully",
            metadata={"source": source},
        )

        self._update_run_status(execution_id, "approved")

        return True, validated_plan

    # ------------------------
    # INTERNAL HELPERS
    # ------------------------
    def _parse_json(self, raw: str):
        try:
            return json.loads(raw), None
        except json.JSONDecodeError as e:
            return None, str(e)

    def _handle_failure(
        self,
        execution_id,
        attempt: int,
        reason: str,
        error: str,
    ):
        if attempt < self.MAX_RETRIES:
            self._persist_decision(
                execution_id,
                decision="retry",
                reason=reason,
                metadata={"attempt": attempt, "error": error},
            )
            return False, None

        self._persist_decision(
            execution_id,
            decision="rejected",
            reason=f"{reason} (max retries exceeded)",
            metadata={"error": error},
        )

        self._update_run_status(execution_id, "rejected")
        return False, None

    def _get_next_version(self, execution_id) -> int:
        count = (
            self.db.query(ExecutionPlan)
            .filter(ExecutionPlan.execution_id == execution_id)
            .count()
        )
        return count + 1

    def _persist_plan(
        self,
        execution_id,
        version,
        plan_json,
        validation_errors,
    ):
        plan = ExecutionPlan(
            execution_id=execution_id,
            version=version,
            plan_json=plan_json,
            validation_errors=validation_errors,
        )
        self.db.add(plan)
        self.db.commit()

    def _persist_decision(
        self,
        execution_id,
        decision,
        reason,
        metadata,
    ):
        record = SupervisorDecision(
            execution_id=execution_id,
            decision=decision,
            reason=reason,
            metadata=metadata,
        )
        self.db.add(record)
        self.db.commit()

    def _update_run_status(self, execution_id, status):
        run = (
            self.db.query(ExecutionRun)
            .filter(ExecutionRun.execution_id == execution_id)
            .first()
        )
        if run:
            run.status = status
            self.db.commit()
