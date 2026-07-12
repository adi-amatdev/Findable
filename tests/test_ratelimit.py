"""Tests for the in-memory IP-based rate limiter.

Covers:
    - First request allowed
    - Requests 2–5 allowed
    - Sixth request rejected (429)
    - Window expiration resets the counter
    - Whitelisted IP bypass
    - Concurrent requests
    - Periodic cleanup of expired entries
    - IP extraction from proxy headers
    - Retry-After header
"""

from __future__ import annotations

import asyncio
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ratelimit.limiter import RateLimiter
from app.ratelimit.middleware import RateLimitMiddleware, extract_client_ip


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(limiter: RateLimiter | None = None, **kwargs) -> FastAPI:
    """Build a minimal FastAPI app with the rate-limit middleware."""
    limiter = limiter or RateLimiter(max_requests=5, window_seconds=43200, **kwargs)
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limiter=limiter)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


def _client(
    limiter: RateLimiter | None = None,
    headers: dict[str, str] | None = None,
    **kwargs,
) -> TestClient:
    return TestClient(_make_app(limiter, **kwargs), headers=headers)


# ---------------------------------------------------------------------------
# Unit tests — RateLimiter
# ---------------------------------------------------------------------------

class TestRateLimiterUnit:
    """Direct tests against the RateLimiter class (no HTTP)."""

    async def test_first_request_allowed(self):
        rl = RateLimiter(max_requests=5, window_seconds=43200)
        assert await rl.allow("10.0.0.1") is True

    async def test_second_through_fifth_allowed(self):
        rl = RateLimiter(max_requests=5, window_seconds=43200)
        for _ in range(4):
            assert await rl.allow("10.0.0.1") is True
        # 5th request (count goes from 4 to 5, still under limit)
        assert await rl.allow("10.0.0.1") is True

    async def test_sixth_request_rejected(self):
        rl = RateLimiter(max_requests=5, window_seconds=43200)
        for _ in range(5):
            assert await rl.allow("10.0.0.1") is True
        assert await rl.allow("10.0.0.1") is False

    async def test_seventh_request_still_rejected(self):
        rl = RateLimiter(max_requests=5, window_seconds=43200)
        for _ in range(5):
            await rl.allow("10.0.0.1")
        assert await rl.allow("10.0.0.1") is False
        assert await rl.allow("10.0.0.1") is False

    async def test_expiration_resets_counter(self):
        rl = RateLimiter(max_requests=5, window_seconds=0.05)
        for _ in range(5):
            assert await rl.allow("10.0.0.1") is True
        assert await rl.allow("10.0.0.1") is False
        # Wait for window to expire
        await asyncio.sleep(0.06)
        assert await rl.allow("10.0.0.1") is True

    async def test_whitelisted_ip_always_allowed(self):
        rl = RateLimiter(
            max_requests=5, window_seconds=43200, whitelist={"127.0.0.1"}
        )
        for _ in range(20):
            assert await rl.allow("127.0.0.1") is True
        assert rl.is_whitelisted("127.0.0.1") is True

    async def test_non_whitelisted_ip_normal_limit(self):
        rl = RateLimiter(
            max_requests=5, window_seconds=43200, whitelist={"127.0.0.1"}
        )
        for _ in range(5):
            await rl.allow("10.0.0.1")
        assert await rl.allow("10.0.0.1") is False

    async def test_separate_ips_independent(self):
        rl = RateLimiter(max_requests=5, window_seconds=43200)
        for _ in range(5):
            await rl.allow("10.0.0.1")
        assert await rl.allow("10.0.0.1") is False
        # Different IP still allowed
        assert await rl.allow("10.0.0.2") is True

    async def test_retry_after_returns_positive_before_expiration(self):
        rl = RateLimiter(max_requests=5, window_seconds=43200)
        await rl.allow("10.0.0.1")
        retry = await rl.retry_after("10.0.0.1")
        assert retry > 0
        assert retry <= 43200

    async def test_retry_after_zero_for_unknown_ip(self):
        rl = RateLimiter(max_requests=5, window_seconds=43200)
        assert await rl.retry_after("10.0.0.1") == 0.0

    async def test_cleanup_removes_expired(self):
        rl = RateLimiter(max_requests=5, window_seconds=0.05)
        await rl.allow("10.0.0.1")
        await rl.allow("10.0.0.2")
        assert rl.size == 2
        await asyncio.sleep(0.06)
        removed = await rl.cleanup()
        assert removed == 2
        assert rl.size == 0

    async def test_cleanup_keeps_fresh_entries(self):
        rl = RateLimiter(max_requests=5, window_seconds=10)
        await rl.allow("10.0.0.1")
        removed = await rl.cleanup()
        assert removed == 0
        assert rl.size == 1

    async def test_reset_removes_bucket(self):
        rl = RateLimiter(max_requests=5, window_seconds=43200)
        await rl.allow("10.0.0.1")
        assert rl.size == 1
        assert await rl.reset("10.0.0.1") is True
        assert rl.size == 0
        # After reset, IP gets a fresh window
        assert await rl.allow("10.0.0.1") is True

    async def test_reset_returns_false_for_unknown_ip(self):
        rl = RateLimiter(max_requests=5, window_seconds=43200)
        assert await rl.reset("10.0.0.1") is False

    async def test_concurrent_requests(self):
        """Flood the limiter with concurrent coroutines.

        With max_requests=10, exactly 10 should be allowed and the rest
        rejected, regardless of scheduling order.
        """
        rl = RateLimiter(max_requests=10, window_seconds=43200)

        async def hit():
            return await rl.allow("10.0.0.1")

        results = await asyncio.gather(*[hit() for _ in range(20)])
        assert sum(results) == 10

    async def test_concurrent_different_ips(self):
        """Concurrent requests from different IPs do not interfere."""
        rl = RateLimiter(max_requests=2, window_seconds=43200)

        async def hit(ip: str):
            return await rl.allow(ip)

        results = await asyncio.gather(
            *[hit("10.0.0.1") for _ in range(5)],
            *[hit("10.0.0.2") for _ in range(5)],
        )
        # Each IP gets exactly 2 allowed
        ip1 = results[:5]
        ip2 = results[5:]
        assert sum(ip1) == 2
        assert sum(ip2) == 2


# ---------------------------------------------------------------------------
# Integration tests — Middleware + HTTP
# ---------------------------------------------------------------------------

class TestRateLimitMiddleware:
    """HTTP-level tests via TestClient."""

    def test_first_request_succeeds(self):
        c = _client()
        resp = c.get("/ok")
        assert resp.status_code == 200

    def test_requests_2_through_5_succeed(self):
        c = _client()
        for _ in range(4):
            resp = c.get("/ok")
            assert resp.status_code == 200
        # 5th
        resp = c.get("/ok")
        assert resp.status_code == 200

    def test_sixth_request_returns_429(self):
        c = _client()
        for _ in range(5):
            c.get("/ok")
        resp = c.get("/ok")
        assert resp.status_code == 429
        body = resp.json()
        assert "Rate limit exceeded" in body["detail"]

    def test_429_includes_retry_after_header(self):
        c = _client()
        for _ in range(5):
            c.get("/ok")
        resp = c.get("/ok")
        assert resp.status_code == 429
        assert "retry-after" in resp.headers
        retry = int(resp.headers["retry-after"])
        assert retry > 0

    def test_expiration_allows_new_requests(self):
        limiter = RateLimiter(max_requests=5, window_seconds=0.05)
        c = _client(limiter=limiter)
        for _ in range(5):
            c.get("/ok")
        resp = c.get("/ok")
        assert resp.status_code == 429
        time.sleep(0.06)
        resp = c.get("/ok")
        assert resp.status_code == 200

    def test_whitelisted_ip_bypasses_limit(self):
        limiter = RateLimiter(
            max_requests=5, window_seconds=43200, whitelist={"testclient"}
        )
        c = _client(limiter=limiter)
        # TestClient sends from host "testclient" by default
        for _ in range(20):
            resp = c.get("/ok")
            assert resp.status_code == 200

    def test_x_forwarded_for_ip(self):
        c = _client(headers={"X-Forwarded-For": "203.0.113.50, 70.41.3.18"})
        resp = c.get("/ok")
        assert resp.status_code == 200
        # 5 more should work (different IP from default testclient)
        for _ in range(4):
            resp = c.get("/ok")
            assert resp.status_code == 200

    def test_x_real_ip_header(self):
        limiter = RateLimiter(
            max_requests=2, window_seconds=43200, whitelist={"testclient"}
        )
        c = _client(limiter=limiter, headers={"X-Real-IP": "198.51.100.7"})
        # First two allowed
        assert c.get("/ok").status_code == 200
        assert c.get("/ok").status_code == 200
        # Third rejected — 198.51.100.7 is not whitelisted
        assert c.get("/ok").status_code == 429

    def test_rate_limiting_applies_to_all_routes(self):
        limiter = RateLimiter(max_requests=2, window_seconds=43200)
        c = _client(limiter=limiter)
        # First two requests allowed (different routes, same IP)
        assert c.get("/ok").status_code == 200
        assert c.get("/health").status_code == 200
        # Third request across any route hits the limit
        assert c.get("/ok").status_code == 429
        assert c.get("/health").status_code == 429

    def test_different_clients_independent(self):
        limiter = RateLimiter(max_requests=1, window_seconds=43200)
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, limiter=limiter)

        @app.get("/ok")
        async def ok():
            return {"status": "ok"}

        client_a = TestClient(app, headers={"X-Real-IP": "10.0.0.1"})
        client_b = TestClient(app, headers={"X-Real-IP": "10.0.0.2"})

        assert client_a.get("/ok").status_code == 200
        assert client_a.get("/ok").status_code == 429
        # Different IP still allowed
        assert client_b.get("/ok").status_code == 200


# ---------------------------------------------------------------------------
# IP extraction
# ---------------------------------------------------------------------------

class TestExtractClientIP:
    """Unit tests for the extract_client_ip helper."""

    def test_x_forwarded_for_single(self):
        from starlette.testclient import TestClient as _TC
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.requests import Request

        async def noop(request: Request):
            ip = extract_client_ip(request)
            from starlette.responses import PlainTextResponse
            return PlainTextResponse(ip)

        app = Starlette(routes=[Route("/ip", noop)])
        c = _TC(app, headers={"X-Forwarded-For": "1.2.3.4"})
        assert c.get("/ip").text == "1.2.3.4"

    def test_x_forwarded_for_multiple(self):
        from starlette.testclient import TestClient as _TC
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.requests import Request

        async def noop(request: Request):
            ip = extract_client_ip(request)
            from starlette.responses import PlainTextResponse
            return PlainTextResponse(ip)

        app = Starlette(routes=[Route("/ip", noop)])
        c = _TC(app, headers={"X-Forwarded-For": "1.2.3.4, 10.0.0.1, 172.16.0.1"})
        assert c.get("/ip").text == "1.2.3.4"

    def test_x_real_ip_fallback(self):
        from starlette.testclient import TestClient as _TC
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.requests import Request

        async def noop(request: Request):
            ip = extract_client_ip(request)
            from starlette.responses import PlainTextResponse
            return PlainTextResponse(ip)

        app = Starlette(routes=[Route("/ip", noop)])
        c = _TC(app, headers={"X-Real-IP": "5.6.7.8"})
        assert c.get("/ip").text == "5.6.7.8"

    def test_empty_x_forwarded_for_falls_through(self):
        from starlette.testclient import TestClient as _TC
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.requests import Request

        async def noop(request: Request):
            ip = extract_client_ip(request)
            from starlette.responses import PlainTextResponse
            return PlainTextResponse(ip)

        app = Starlette(routes=[Route("/ip", noop)])
        c = _TC(app, headers={"X-Forwarded-For": ""})
        # Falls through to client.host which is "testclient" in TestClient
        assert c.get("/ip").text == "testclient"
