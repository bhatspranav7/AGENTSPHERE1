import logging
import uuid

from backend.app.core.llm_client import LLMClient
from backend.app.core.prompts import PLANNER_SYSTEM_PROMPT
from backend.app.agents.supervisor_agent import SupervisorAgent
from backend.app.models.execution import ExecutionRun
from backend.app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    Planner generates plans.
    Supervisor validates and approves them.
    """

    def __init__(self):
        self.llm = LLMClient()
        self.supervisor = SupervisorAgent()
        self.db = SessionLocal()

    def create_plan(self, user_objective: str):
        execution_id = uuid.uuid4()

        run = ExecutionRun(
            execution_id=execution_id,
            user_objective=user_objective,
            source="ollama",
            status="planned",
        )
        self.db.add(run)
        self.db.commit()

        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
User objective:
{user_objective}

Return ONLY valid JSON matching schema.
""",
            },
        ]

        attempt = 0

        while True:
            response = self.llm.generate(messages)
            raw_output = response["content"]

            approved, plan = self.supervisor.review_plan(
                execution_id=execution_id,
                raw_plan_output=raw_output,
                source="ollama",
                attempt=attempt,
            )

            if approved:
                return execution_id, plan

            attempt += 1

            if attempt > self.supervisor.MAX_RETRIES:
                raise RuntimeError(
                    f"Execution {execution_id} rejected by Supervisor"
                )
