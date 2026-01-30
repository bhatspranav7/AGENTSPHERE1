# backend/app/llm/factory.py
import os
from app.llm.dummy_llm import DummyLLM

def get_llm():
    if os.getenv("OPENAI_API_KEY"):
        try:
            from app.llm.openai_llm import OpenAILLM
            return OpenAILLM()
        except Exception:
            pass

    return DummyLLM()
