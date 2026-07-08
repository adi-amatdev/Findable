"""Cache: stable keys and graceful degradation when Redis is unreachable."""

from __future__ import annotations

from app.cache import Cache, make_key
from app.config import Settings


def test_make_key_is_stable_and_url_sensitive():
    assert make_key("https://a.com") == make_key("https://a.com")
    assert make_key("https://a.com") != make_key("https://b.com")
    assert make_key("https://a.com", "crawl") != make_key("https://a.com", "report")


async def test_cache_degrades_gracefully_without_redis():
    # Point at a port with nothing listening.
    cache = Cache(Settings(redis_url="redis://127.0.0.1:6399/0", cache_enabled=True))
    key = make_key("https://example.com")
    assert await cache.get(key) is None       # miss, no exception
    await cache.set(key, {"a": 1})             # no-op, no exception
    assert await cache.ping() is False
    await cache.close()


async def test_cache_disabled_is_noop():
    cache = Cache(Settings(cache_enabled=False))
    assert cache.enabled is False
    assert await cache.get(make_key("https://example.com")) is None
    await cache.set(make_key("https://example.com"), {"a": 1})
