from typing import Any, Dict
from app.memory.agent_memory import AgentMemory

class SupervisorAgent:
    name = "supervisor_agent"

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    def validate_output(self, agent_name: str, output: Dict[str, Any]) -> bool:
        if not output:
            return False

        if agent_name == "research_agent":
            return "summary" in output

        return True

    def supervise(
        self,
        agent_name: str,
        output: Dict[str, Any],
        attempt: int,
        workflow_id: str
    ) -> Dict[str, Any]:

        if self.validate_output(agent_name, output):
            decision = "APPROVE"
        elif attempt < self.max_retries:
            decision = "RETRY"
        else:
            decision = "ABORT"

        log = {
            "agent": agent_name,
            "decision": decision,
            "attempt": attempt
        }

        AgentMemory.save_workflow_memory(workflow_id, {
            "supervisor": log
        })

        return log
