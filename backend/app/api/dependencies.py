from fastapi import Header, HTTPException, status
from backend.app.core.security import APIKeyValidator


async def api_key_auth(x_api_key: str = Header(default=None)):
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing",
        )

    if not APIKeyValidator.validate(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return x_api_key
