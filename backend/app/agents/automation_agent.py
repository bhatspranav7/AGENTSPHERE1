from backend.app.agents.base_agent import BaseExecutionAgent


class AutomationAgent(BaseExecutionAgent):
    agent_name = "automation"

    def execute(self, execution_id, step):
        return {
            "status": "completed",
            "message": f"Automation finished for: {step['objective']}"
        }
