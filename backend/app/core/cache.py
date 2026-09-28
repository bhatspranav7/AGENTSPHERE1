"""Redis access with a transparent in-process fallback.

Redis backs short-term agent memory, rate limiting and cross-run state. When it
is unreachable the app keeps working on a small in-memory store and reports
`cache: in-memory` on /health instead of failing.
"""
import json
import logging
import threading
import time
from typing import Any

import redis

from .config import settings

logger = logging.getLogger(__name__)


class InMemoryCache:
    def __init__(self):
        self._kv: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.Lock()

    def _get(self, key):
        item = self._kv.get(key)
        if item is None:
            return None
        value, expires = item
        if expires is not None and expires <= time.monotonic():
            del self._kv[key]
            return None
        return value

    def ping(self):
        return True

    def incr(self, key):
        with self._lock:
            value = int(self._get(key) or 0) + 1
            expires = self._kv.get(key, (None, None))[1]
            self._kv[key] = (value, expires)
            return value

    def expire(self, key, seconds):
        with self._lock:
            value = self._get(key)
            if value is None:
                return False
            self._kv[key] = (value, time.monotonic() + seconds)
            return True

    def ttl(self, key):
        with self._lock:
            if self._get(key) is None:
                return -2
            expires = self._kv[key][1]
            return -1 if expires is None else int(expires - time.monotonic())

    def rpush(self, key, *values):
        with self._lock:
            items = list(self._get(key) or [])
            items.extend(values)
            expires = self._kv.get(key, (None, None))[1]
            self._kv[key] = (items, expires)
            return len(items)

    def lrange(self, key, start, end):
        with self._lock:
            items = list(self._get(key) or [])
        end = len(items) if end == -1 else end + 1
        return items[start:end]

    def delete(self, *keys):
        with self._lock:
            return sum(1 for k in keys if self._kv.pop(k, None) is not None)


def _connect():
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        logger.info("Connected to Redis")
        return client, "redis"
    except Exception as e:
        logger.warning("Redis unavailable (%s) - using in-memory cache", e)
        return InMemoryCache(), "in-memory"


cache, CACHE_MODE = _connect()


# -------------------------------------------------
# WORKFLOW MEMORY (short-term, per execution)
# -------------------------------------------------
MEMORY_TTL_SECONDS = 24 * 3600


def remember(execution_id: str, entry: dict):
    key = f"workflow_memory:{execution_id}"
    try:
        cache.rpush(key, json.dumps(entry, default=str))
        cache.expire(key, MEMORY_TTL_SECONDS)
    except Exception as e:
        logger.warning("Memory write failed: %s", e)


def recall(execution_id: str) -> list[dict]:
    try:
        return [json.loads(e) for e in cache.lrange(f"workflow_memory:{execution_id}", 0, -1)]
    except Exception as e:
        logger.warning("Memory read failed: %s", e)
        return []
