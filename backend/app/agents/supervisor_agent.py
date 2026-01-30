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
    Intelligent Supervisor:
    - Validates planner output
    - Classifies failures
    - Controls retries
    - Persists explainable decisions
    """

    MAX_RETRIES = 2

    def __init__(self):
        self.db: Session = SessionLocal()

    # ========================
    # PUBLIC ENTRY POINT
    # ========================
    def review_plan(
        self,
        execution_id,
        raw_plan_output: str,
        source: str,
        attempt: int,
    ) -> Tuple[bool, Optional[PlanSchema], Optional[str]]:
        """
        Returns:
        - approved (bool)
        - validated plan (or None)
        - retry_hint (or None)
        """

        plan_json, parse_error = self._parse_json(raw_plan_output)
        version = self._next_version(execution_id)

        # ------------------------
        # JSON PARSE FAILURE
        # ------------------------
        if parse_error:
            self._persist_plan(
                execution_id,
                version,
                None,
                {"type": "invalid_json", "error": parse_error},
            )

            return self._handle_failure(
                execution_id,
                attempt,
                failure_type="invalid_json",
                reason="Planner returned invalid JSON",
                retry_hint="Return ONLY valid JSON. Do not include explanations.",
            )

        # ------------------------
        # SCHEMA VALIDATION FAILURE
        # ------------------------
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
                failure_type="schema_error",
                reason="Planner output failed schema validation",
                retry_hint="Fix missing or incorrect fields. Follow schema strictly.",
            )

        # ------------------------
        # SUCCESS
        # ------------------------
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
            metadata={"source": source, "version": version},
        )

        self._update_run_status(execution_id, "approved")

        return True, validated_plan, None

    # ========================
    # FAILURE HANDLING
    # ========================
    def _handle_failure(
        self,
        execution_id,
        attempt: int,
        failure_type: str,
        reason: str,
        retry_hint: str,
    ):
        if attempt < self.MAX_RETRIES:
            self._persist_decision(
                execution_id,
                decision="retry",
                reason=reason,
                metadata={
                    "attempt": attempt,
                    "failure_type": failure_type,
                },
            )
            return False, None, retry_hint

        self._persist_decision(
            execution_id,
            decision="rejected",
            reason=f"{reason} (max retries exceeded)",
            metadata={"failure_type": failure_type},
        )

        self._update_run_status(execution_id, "rejected")
        return False, None, None

    # ========================
    # DB HELPERS
    # ========================
    def _next_version(self, execution_id) -> int:
        return (
            self.db.query(ExecutionPlan)
            .filter(ExecutionPlan.execution_id == execution_id)
            .count()
            + 1
        )

    def _persist_plan(
        self,
        execution_id,
        version,
        plan_json,
        validation_errors,
    ):
        record = ExecutionPlan(
            execution_id=execution_id,
            version=version,
            plan_json=plan_json,
            validation_errors=validation_errors,
        )
        self.db.add(record)
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

    # ========================
    # UTIL
    # ========================
    def _parse_json(self, raw: str):
        try:
            return json.loads(raw), None
        except json.JSONDecodeError as e:
            return None, str(e)
