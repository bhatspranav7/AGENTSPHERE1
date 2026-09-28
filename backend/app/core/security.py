import hmac
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Query, Request

from .cache import cache
from .config import settings


@dataclass(frozen=True)
class Principal:
    role: str  # "admin" | "demo"
    client: str


def _matches(candidate: str, key: str) -> bool:
    return bool(key) and hmac.compare_digest(candidate.encode(), key.encode())


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None),
    api_key: str | None = Query(default=None, include_in_schema=False),
) -> Principal:
    """
    Verifies the X-API-Key header for all protected endpoints.
    `?api_key=` is accepted too because browser EventSource can't set headers.
    """
    candidate = x_api_key or api_key
    if not candidate:
        raise HTTPException(status_code=401, detail={"error": "Missing API key"})

    if any(_matches(candidate, k) for k in settings.admin_keys):
        return Principal("admin", _client_ip(request))

    if _matches(candidate, settings.DEMO_API_KEY):
        return Principal("demo", _client_ip(request))

    raise HTTPException(status_code=401, detail={"error": "Invalid API key"})


def enforce_rate_limit(principal: Principal = Depends(verify_api_key)) -> Principal:
    """Fixed-window limit on launching executions with the public demo key."""
    if principal.role != "demo":
        return principal

    key = f"ratelimit:demo:{principal.client}"
    count = cache.incr(key)
    if count == 1:
        cache.expire(key, 3600)

    if count > settings.DEMO_RATE_LIMIT_PER_HOUR:
        retry_after = max(cache.ttl(key), 1)
        raise HTTPException(
            status_code=429,
            detail={"error": f"Demo limit of {settings.DEMO_RATE_LIMIT_PER_HOUR} runs/hour reached"},
            headers={"Retry-After": str(retry_after)},
        )
    return principal
