# backend/app/llm/openai_llm.py
import os
from app.llm.base import BaseLLM

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class OpenAILLM(BaseLLM):
    def __init__(self):
        if not OpenAI:
            raise RuntimeError("openai package not installed")

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate(self, prompt: str):
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an intelligent planning agent."},
                {"role": "user", "content": prompt}
            ]
        )

        return {
            "content": response.choices[0].message.content
        }
