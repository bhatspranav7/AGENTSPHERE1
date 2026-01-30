# backend/app/llm/dummy_llm.py
from app.llm.base import BaseLLM

class DummyLLM(BaseLLM):
    def generate(self, prompt: str):
        return {
            "content": "LLM disabled. Using fallback logic.",
            "raw_prompt": prompt
        }
