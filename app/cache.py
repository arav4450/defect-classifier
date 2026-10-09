"""
Cache layer.

12-factor principle: backing services are attached resources, swapped via
config, not code. CACHE_BACKEND=memory works with zero setup for local dev
or a quick demo; CACHE_BACKEND=redis is a one-env-var swap for anything
that needs to survive a pod restart or be shared across replicas.

Cache key = hash of (image bytes + candidate labels), since that's the
full input to the model — identical input always gives identical output.
"""

import hashlib
import json
import time
from typing import Optional

from cachetools import TTLCache

from app.config import settings


def make_cache_key(image_bytes: bytes, labels: list[str]) -> str:
    hasher = hashlib.sha256()
    hasher.update(image_bytes)
    hasher.update(json.dumps(sorted(labels)).encode("utf-8"))
    return hasher.hexdigest()


class BaseCache:
    def get(self, key: str) -> Optional[dict]:
        raise NotImplementedError

    def set(self, key: str, value: dict) -> None:
        raise NotImplementedError


class MemoryCache(BaseCache):
    """In-process TTL cache. Simple, but private to a single replica —
    fine for a demo, not for multi-pod production (use Redis there)."""

    def __init__(self, maxsize: int, ttl: int):
        self._store: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str) -> Optional[dict]:
        return self._store.get(key)

    def set(self, key: str, value: dict) -> None:
        self._store[key] = value


class RedisCache(BaseCache):
    """Shared cache across replicas. Requires REDIS_URL to point at a
    reachable Redis instance (a real backing service)."""

    def __init__(self, url: str, ttl: int):
        import redis  # imported lazily so redis-py isn't required for memory mode

        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._ttl = ttl

    def get(self, key: str) -> Optional[dict]:
        raw = self._client.get(key)
        return json.loads(raw) if raw else None

    def set(self, key: str, value: dict) -> None:
        self._client.setex(key, self._ttl, json.dumps(value))


def build_cache() -> BaseCache:
    if settings.CACHE_BACKEND == "redis":
        return RedisCache(settings.REDIS_URL, settings.CACHE_TTL_SECONDS)
    return MemoryCache(settings.CACHE_MAX_ITEMS, settings.CACHE_TTL_SECONDS)


cache = build_cache()
_start_time = time.time()


def uptime_seconds() -> float:
    return time.time() - _start_time
