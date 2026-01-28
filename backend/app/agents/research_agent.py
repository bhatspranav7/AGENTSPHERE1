from typing import Dict, Any
from app.memory.agent_memory import AgentMemory

class ResearchAgent:
    name = "research_agent"

    def run(self, topic: str, workflow_id: str) -> Dict[str, Any]:
        output = {
            "summary": f"Research completed on topic: {topic}",
            "confidence": 0.92
        }

        AgentMemory.save_workflow_memory(
            workflow_id,
            {
                "agent": self.name,
                "output": output
            }
        )

        AgentMemory.save_agent_memory(self.name, output)

        return output
