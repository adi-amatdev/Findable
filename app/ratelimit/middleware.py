"""Starlette middleware that enforces IP-based rate limiting.

The middleware sits in front of every route and either passes the request
through or returns HTTP 429 with a ``Retry-After`` header.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .limiter import RateLimiter

logger = logging.getLogger(__name__)


def extract_client_ip(request: Request) -> str:
    """Derive the client IP from trusted proxy headers.

    Assumes the service runs behind a trusted reverse proxy (Caddy) so
    ``X-Forwarded-For`` and ``X-Real-IP`` are authoritative.

    Priority:
        1. ``X-Forwarded-For`` — first comma-separated value (original client).
        2. ``X-Real-IP``
        3. Socket ``client.host`` (direct connection).
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip()
        if ip:
            return ip

    xri = request.headers.get("x-real-ip")
    if xri:
        ip = xri.strip()
        if ip:
            return ip

    if request.client:
        return request.client.host

    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that applies a :class:`RateLimiter` to every request."""

    def __init__(self, app, limiter: RateLimiter) -> None:  # noqa: D107
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = extract_client_ip(request)

        if await self.limiter.allow(client_ip):
            return await call_next(request)

        retry = await self.limiter.retry_after(client_ip)
        retry_header = str(int(retry)) if retry > 0 else "0"
        logger.info("Rate limit exceeded for %s", client_ip)
        return JSONResponse(
            status_code=429,
            content={
                "detail": (
                    "Rate limit exceeded. You may make up to 5 requests "
                    "every 12 hours."
                )
            },
            headers={"Retry-After": retry_header},
        )
