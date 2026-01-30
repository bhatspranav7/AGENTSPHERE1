import os
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)


class LLMConfig(BaseModel):
    provider: str = "ollama"
    model: str = "llama3.2:latest"
    temperature: float = 0.3
    max_tokens: int = 1200
    timeout: int = 60
    base_url: str = "http://localhost:11434"


class AppConfig(BaseModel):
    app_name: str = "AgentSphere"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str
    llm: LLMConfig


@lru_cache()
def get_config() -> AppConfig:
    return AppConfig(
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        database_url=os.getenv("DATABASE_URL"),
        llm=LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "ollama"),
            model=os.getenv("OLLAMA_MODEL", "llama3.2:latest"),
            temperature=float(os.getenv("LLM_TEMPERATURE", 0.3)),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", 1200)),
            timeout=int(os.getenv("LLM_TIMEOUT", 60)),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ),
    )
