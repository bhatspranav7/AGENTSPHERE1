from backend.app.db.session import SessionLocal
from backend.app.models.agent_execution import AgentExecution

from backend.app.agents.research_agent import ResearchAgent
from backend.app.agents.code_agent import CodeAgent
from backend.app.agents.automation_agent import AutomationAgent
from backend.app.agents.supervisor_agent import SupervisorAgent


class ExecutionEngine:

    def __init__(self):
        self.agent_map = {
            "ResearchAgent": ResearchAgent(),
            "CodeAgent": CodeAgent(),
            "AutomationAgent": AutomationAgent(),
            "SupervisorAgent": SupervisorAgent(),
        }

    def run(self, execution_id, plan: dict):

        steps = plan.get("steps", [])
        db = SessionLocal()

        try:
            for step in steps:

                agent_name = step.get("agent")
                task = step.get("task")

                agent = self.agent_map.get(agent_name)

                result = None

                if agent:
                    print(f"Running {agent_name} with task:", task)
                    result = agent.run(task)

                record = AgentExecution(
                    execution_id=execution_id,
                    step_id=step.get("step_id"),
                    agent_name=agent_name,
                    output_payload={
                        "task": task,
                        "result": result or "executed"
                    },
                    status="completed",
                )

                db.add(record)

            db.commit()

        finally:
            db.close()
