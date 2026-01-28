# app/agents/planner_agent.py

import os
from typing import List, Dict


class PlannerAgent:
    def __init__(self):
        self.llm_enabled = False
        self.client = None

        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
                self.llm_enabled = True
            except Exception as e:
                print(f"⚠️ OpenAI disabled: {e}")

    def plan(self, query: str) -> List[Dict]:
        """
        If LLM is enabled → use it
        Else → fallback static planner
        """

        if self.llm_enabled:
            return self._llm_plan(query)

        # 🔹 SAFE FALLBACK (NO LLM)
        return [
            {
                "agent": "research_agent",
                "input": {"query": query}
            },
            {
                "agent": "code_agent",
                "input": {}
            },
            {
                "agent": "automation_agent",
                "input": {}
            }
        ]

    def _llm_plan(self, query: str) -> List[Dict]:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a planner agent. Output JSON only."
                },
                {
                    "role": "user",
                    "content": f"Create a step-by-step agent plan for: {query}"
                }
            ]
        )

        return eval(response.choices[0].message.content)
