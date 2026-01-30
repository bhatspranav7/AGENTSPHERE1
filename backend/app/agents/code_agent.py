from backend.app.agents.base_agent import BaseExecutionAgent


class CodeAgent(BaseExecutionAgent):
    agent_name = "code"

    def execute(self, execution_id, step):
        """
        Deterministic code generation.
        (Later can be LLM-powered or hybrid)
        """

        objective = step["objective"]

        return {
            "description": f"Code generated for objective: {objective}",
            "files": [
                {
                    "filename": "main.py",
                    "content": "# Sample FastAPI application\n\nprint('Hello from CodeAgent')"
                }
            ],
            "notes": "This is a deterministic placeholder implementation."
        }
