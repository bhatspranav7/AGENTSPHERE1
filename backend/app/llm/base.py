# backend/app/llm/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> Dict[str, Any]:
        pass
