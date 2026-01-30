from backend.app.agents.base_agent import BaseExecutionAgent


class CodeAgent(BaseExecutionAgent):
    agent_name = "code"

    def execute(self, execution_id, step):
        return {
            "description": f"Code generated for: {step['objective']}",
            "files": [
                {
                    "filename": "main.py",
                    "content": "print('Hello from AgentSphere CodeAgent')"
                }
            ],
            "notes": "Deterministic code output"
        }
