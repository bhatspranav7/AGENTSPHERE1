from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from ..core.config import settings


@dataclass
class LLMResponse:
    data: dict[str, Any]
    tokens: int = 0
    latency_ms: int = 0
    model: str = ""
    raw: str = field(default="", repr=False)


class LLM(Protocol):
    mode: str
    model: str

    def complete_json(self, task: str, system: str, user: str, sim: dict[str, Any]) -> LLMResponse:
        """Return a JSON object for `task`.

        `sim` carries structured context the simulated backend uses instead of
        free text; real LLMs only see `system` and `user`.
        """
        ...


@lru_cache
def get_llm() -> LLM:
    if settings.llm_enabled:
        from .openai_compat import OpenAICompatibleLLM
        return OpenAICompatibleLLM()

    from .simulated import SimulatedLLM
    return SimulatedLLM()
