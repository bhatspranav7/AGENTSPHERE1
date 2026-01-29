import json
import logging

from backend.app.core.llm_client import LLMClient
from backend.app.core.prompts import PLANNER_SYSTEM_PROMPT
from backend.app.models.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    LLM-powered Planner Agent.
    """

    def __init__(self):
        self.llm = LLMClient()

    def create_plan(self, user_objective: str) -> ExecutionPlan:
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
User objective:
{user_objective}

Return ONLY valid JSON matching this schema:
{{
  "user_objective": string,
  "steps": [
    {{
      "step_id": number,
      "agent": "research | code | automation | supervisor",
      "objective": string,
      "inputs": [string],
      "expected_output": string
    }}
  ]
}}
""",
            },
        ]

        response = self.llm.generate(messages)
        raw_output = response["content"]

        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError as e:
            raise ValueError("Planner returned invalid JSON") from e

        return ExecutionPlan.model_validate(parsed)
