from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # -------------------------------------------------
    # DATABASE
    # -------------------------------------------------
    DATABASE_URL: str = "postgresql://agentsphere:agentsphere@localhost:5432/agentsphere_db"

    # -------------------------------------------------
    # SECURITY
    # -------------------------------------------------
    API_KEY: str = "agentsphere-dev-key"

    class Config:
        env_file = ".env"


# -------------------------------------------------
# SINGLETON SETTINGS OBJECT
# -------------------------------------------------
settings = Settings()
