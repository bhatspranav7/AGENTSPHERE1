from backend.app.agents.base_agent import BaseExecutionAgent


class ResearchAgent(BaseExecutionAgent):
    agent_name = "research"

    def execute(self, execution_id, step):
        return {
            "summary": f"Research completed for: {step['objective']}",
            "assumptions": [
                "Standard constraints apply",
                "No external blockers identified"
            ],
            "notes": "Deterministic research output"
        }
