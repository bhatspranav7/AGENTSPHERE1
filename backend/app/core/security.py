from fastapi import Header, HTTPException, Depends
from backend.app.core.config import settings


def verify_api_key(x_api_key: str = Header(...)):
    """
    Verifies X-API-Key header for all protected endpoints.
    """

    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid or missing API key"},
        )

    return True
