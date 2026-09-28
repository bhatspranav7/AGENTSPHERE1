from functools import cached_property
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # -------------------------------------------------
    # DATABASE / CACHE
    # -------------------------------------------------
    DATABASE_URL: str = "postgresql://agentsphere:agentsphere@localhost:5432/agentsphere_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # -------------------------------------------------
    # SECURITY
    # -------------------------------------------------
    # Comma-separated admin keys. API_KEY is kept for backward compatibility.
    API_KEYS: str = ""
    API_KEY: str = "agentsphere-dev-key"
    # Optional public key the UI may auto-use; rate limited per client IP.
    DEMO_API_KEY: str = ""
    DEMO_RATE_LIMIT_PER_HOUR: int = 20
    CORS_ORIGINS: str = "*"

    # -------------------------------------------------
    # LLM (any OpenAI-compatible endpoint: OpenAI, Groq, Ollama /v1, OpenRouter...)
    # -------------------------------------------------
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: float = 45
    LLM_TEMPERATURE: float = 0.3
    # "auto" = real LLM when a key (or local base URL) is configured, else simulated
    LLM_MODE: str = "auto"

    # -------------------------------------------------
    # ORCHESTRATION
    # -------------------------------------------------
    MAX_STEP_RETRIES: int = 2
    MAX_PLAN_RETRIES: int = 2
    MAX_PLAN_STEPS: int = 8
    WORKER_THREADS: int = 4
    STEP_PARALLELISM: int = 3
    SIMULATED_LATENCY: float = 1.0  # multiplier for simulated agent "thinking" time

    FRONTEND_DIR: str = str(Path(__file__).resolve().parents[2] / "static")

    @cached_property
    def database_url(self) -> str:
        url = self.DATABASE_URL
        # Render / Heroku hand out postgres:// which SQLAlchemy 2 rejects
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        return url

    @cached_property
    def admin_keys(self) -> set[str]:
        keys = {k.strip() for k in self.API_KEYS.split(",") if k.strip()}
        if self.API_KEY:
            keys.add(self.API_KEY)
        return keys

    @cached_property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @cached_property
    def llm_enabled(self) -> bool:
        mode = self.LLM_MODE.lower()
        if mode == "simulated":
            return False
        if mode == "live":
            return True
        local = any(h in self.LLM_BASE_URL for h in ("localhost", "127.0.0.1", "ollama", "host.docker.internal"))
        return bool(self.LLM_API_KEY) or local


settings = Settings()
