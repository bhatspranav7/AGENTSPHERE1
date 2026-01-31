from backend.app.config.settings import settings


class APIKeyValidator:
    @staticmethod
    def validate(api_key: str) -> bool:
        return api_key in settings.api_key_list
