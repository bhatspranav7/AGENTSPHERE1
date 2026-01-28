import uuid
from typing import Dict, Any

from app.agents.research_agent import ResearchAgent
from app.agents.supervisor_agent import SupervisorAgent

class WorkflowOrchestrator:

    def __init__(self):
        self.research_agent = ResearchAgent()
        self.supervisor = SupervisorAgent()

    def execute(self, topic: str) -> Dict[str, Any]:
        workflow_id = str(uuid.uuid4())
        attempt = 0

        while True:
            output = self.research_agent.run(topic, workflow_id)

            supervisor_decision = self.supervisor.supervise(
                agent_name=self.research_agent.name,
                output=output,
                attempt=attempt,
                workflow_id=workflow_id
            )

            if supervisor_decision["decision"] == "APPROVE":
                return {
                    "workflow_id": workflow_id,
                    "status": "SUCCESS",
                    "result": output,
                    "supervisor": supervisor_decision
                }

            if supervisor_decision["decision"] == "ABORT":
                return {
                    "workflow_id": workflow_id,
                    "status": "FAILED",
                    "supervisor": supervisor_decision
                }

            attempt += 1
