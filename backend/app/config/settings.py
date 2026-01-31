from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_KEYS: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def api_key_list(self) -> list[str]:
        return [k.strip() for k in self.API_KEYS.split(",") if k.strip()]


settings = Settings()
