"""Redis cache. Check-first, graceful degradation on any Redis error.

We cache the raw crawl (RawCrawl) keyed by a hash of the URL, so re-runs and
demo runs never re-fetch and never waste Firecrawl credits. A Redis outage
degrades to a cache miss / no-op — it never breaks the pipeline.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import Any, Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

from ..config import Settings, get_settings

KEY_PREFIX = "findable:crawl:"


def make_key(url: str, namespace: str = "crawl", extra: Any = None) -> str:
    """Stable cache key from the URL (and optional extra discriminator)."""
    payload = json.dumps({"url": url, "extra": extra}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"findable:{namespace}:{digest}"


class Cache:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: Optional[redis.Redis] = None

    @property
    def enabled(self) -> bool:
        return self._settings.cache_enabled

    def _get_client(self) -> Optional[redis.Redis]:
        if not self.enabled:
            return None
        if self._client is None:
            self._client = redis.from_url(self._settings.redis_url, decode_responses=True)
        return self._client

    async def get(self, key: str) -> Optional[dict]:
        client = self._get_client()
        if client is None:
            return None
        try:
            raw = await client.get(key)
        except RedisError:
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return None

    async def set(self, key: str, value: dict) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            raw = json.dumps(value)
        except (TypeError, ValueError):
            return
        ttl = self._settings.cache_ttl_seconds
        try:
            if ttl and ttl > 0:
                await client.set(key, raw, ex=ttl)
            else:
                await client.set(key, raw)
        except RedisError:
            return

    async def ping(self) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            return bool(await client.ping())
        except RedisError:
            return False

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except RedisError:
                pass
            self._client = None


@lru_cache
def get_cache() -> Cache:
    return Cache(get_settings())
