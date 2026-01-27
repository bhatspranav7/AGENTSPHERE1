from typing import Dict, List
from app.workflows.task_graph import Task, TaskGraph
import uuid


class PlannerAgent:
    """
    PlannerAgent is responsible for converting a user request
    into a structured execution plan (TaskGraph).
    """

    def plan(self, workflow_id: int, user_request: str) -> TaskGraph:
        """
        This is where an LLM will be used later.
        For now, we simulate a deterministic enterprise-style plan.
        """

        tasks: List[Task] = [
            Task(
                task_id=str(uuid.uuid4()),
                agent="research_agent",
                action="research_topic",
                input={"query": user_request},
            ),
            Task(
                task_id=str(uuid.uuid4()),
                agent="code_agent",
                action="generate_solution",
                input={"context": "research results"},
            ),
            Task(
                task_id=str(uuid.uuid4()),
                agent="automation_agent",
                action="trigger_output",
                input={"destination": "user"},
            ),
        ]

        return TaskGraph(
            workflow_id=workflow_id,
            tasks=tasks
        )
