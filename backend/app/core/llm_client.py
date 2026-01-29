import logging
import time
import requests
from typing import List, Dict, Any

from backend.app.core.config import get_config

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Ollama-based LLM client (FAULT-TOLERANT).
    Never blocks AgentSphere execution.
    """

    def __init__(self):
        self.config = get_config()
        self.base_url = self.config.llm.base_url.strip().rstrip("/")
        self.model = self.config.llm.model

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Dict[str, Any]:
        prompt = self._messages_to_prompt(messages)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.llm.temperature,
                "num_predict": min(
                    max_tokens or self.config.llm.max_tokens,
                    300,  # HARD CAP to avoid hangs
                ),
            },
        }

        endpoint = f"{self.base_url}/api/generate"

        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=20,  # ⬅ MUCH LOWER TIMEOUT
            )
            response.raise_for_status()

            data = response.json()

            return {
                "content": data.get("response", "").strip(),
                "usage": {},
                "latency": None,
            }

        except Exception as e:
            # 🔥 DO NOT FAIL SYSTEM BECAUSE OF LLM
            logger.warning(
                "Ollama unavailable, using fallback planner output",
                extra={"error": str(e)},
            )

            return {
                "content": self._fallback_plan(),
                "usage": {},
                "latency": None,
            }

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        parts = []
        for msg in messages:
            parts.append(f"{msg['role'].upper()}:\n{msg['content'].strip()}")
        parts.append("ASSISTANT:\n")
        return "\n\n".join(parts)

    def _fallback_plan(self) -> str:
        """
        Deterministic fallback so AgentSphere NEVER blocks.
        """
        return """
{
  "user_objective": "Fallback plan",
  "steps": [
    {
      "step_id": 1,
      "agent": "research",
      "objective": "Analyze the task requirements",
      "inputs": [],
      "expected_output": "Clear understanding of the problem"
    },
    {
      "step_id": 2,
      "agent": "code",
      "objective": "Implement a basic solution",
      "inputs": ["requirements"],
      "expected_output": "Working code"
    },
    {
      "step_id": 3,
      "agent": "supervisor",
      "objective": "Review the output",
      "inputs": ["code output"],
      "expected_output": "Approved or revision request"
    }
  ]
}
"""
