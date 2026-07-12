"""In-memory IP-based rate limiter with automatic expiration.

Algorithm:
    Each client IP gets a single sliding window bucket:
        { count: int, expires_at: float }

    On every request:
        1. If the IP has no bucket or the bucket is expired → create a fresh
           bucket (count=1, expires_at=now+window).
        2. Otherwise, if count < max_requests → increment and allow.
        3. Otherwise → reject.

    Expired buckets are cleaned up both lazily (on the next access for that IP)
    and periodically (via `cleanup()`) to bound memory usage.

Designed to be swapped for a Redis-backed implementation later — callers
interact only through `allow()` / `retry_after()`, never touching the
internal map directly.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass(slots=True)
class _Bucket:
    """Rate-limit state for a single IP within one window."""

    count: int
    expires_at: float


class RateLimiter:
    """In-memory, asyncio-safe rate limiter.

    Parameters
    ----------
    max_requests:
        Maximum number of requests allowed within the window.
    window_seconds:
        Length of the rate-limit window in seconds.
    whitelist:
        IP addresses that bypass rate limiting entirely.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        whitelist: set[str] | None = None,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._whitelist: set[str] = whitelist or set()
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def is_whitelisted(self, ip: str) -> bool:
        """Return True if *ip* bypasses rate limiting."""
        return ip in self._whitelist

    async def allow(self, ip: str) -> bool:
        """Return True if the request should be allowed.

        Whitelisted IPs always pass.  For everyone else the method atomically
        checks (and increments) the counter, creating or resetting the bucket
        when the window has expired.
        """
        if self.is_whitelisted(ip):
            return True

        now = time.monotonic()

        async with self._lock:
            bucket = self._buckets.get(ip)

            # No bucket or window expired → start a new window.
            if bucket is None or now >= bucket.expires_at:
                self._buckets[ip] = _Bucket(
                    count=1, expires_at=now + self._window_seconds
                )
                return True

            # Still inside the window — check the counter.
            if bucket.count < self._max_requests:
                bucket.count += 1
                return True

            # Limit reached.
            return False

    async def retry_after(self, ip: str) -> float:
        """Seconds until the current window resets for *ip*.

        Returns 0 when there is no active bucket (the next request will
        start a fresh window).
        """
        async with self._lock:
            bucket = self._buckets.get(ip)
            if bucket is None:
                return 0.0
            return max(0.0, bucket.expires_at - time.monotonic())

    async def cleanup(self) -> int:
        """Remove all expired buckets.  Returns the count removed."""
        now = time.monotonic()
        async with self._lock:
            expired = [ip for ip, b in self._buckets.items() if now >= b.expires_at]
            for ip in expired:
                del self._buckets[ip]
            return len(expired)

    async def reset(self, ip: str) -> bool:
        """Remove the bucket for *ip* unconditionally.

        Useful for testing and administrative overrides.
        """
        async with self._lock:
            return self._buckets.pop(ip, None) is not None

    @property
    def size(self) -> int:
        """Number of active (non-expired) buckets — approximate, no lock."""
        return len(self._buckets)
