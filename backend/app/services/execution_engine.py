from backend.app.agents.research_agent import ResearchAgent
from backend.app.agents.code_agent import CodeAgent
from backend.app.agents.automation_agent import AutomationAgent
from backend.app.db.session import SessionLocal
from backend.app.models.agent_execution import AgentExecution


class ExecutionEngine:
    def __init__(self):
        self.db = SessionLocal()
        self.agents = {
            "research": ResearchAgent(),
            "code": CodeAgent(),
            "automation": AutomationAgent(),
        }

    def run(self, execution_id, plan):
        for step in plan.steps:
            agent = self.agents.get(step.agent)

            if not agent:
                raise ValueError(f"No agent registered for {step.agent}")

            output = agent.execute(execution_id, step.model_dump())

            record = AgentExecution(
                execution_id=execution_id,
                step_id=step.step_id,
                agent_name=step.agent,
                input_payload=step.model_dump(),
                output_payload=output,
                status="completed",
            )

            self.db.add(record)
            self.db.commit()
