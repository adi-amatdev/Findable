---
type: Component
title: IP-Based Rate Limiter
description: In-memory sliding-window rate limiter applied as ASGI middleware. Limits requests per client IP with configurable whitelist, lazy + periodic expired-entry cleanup.
tags: [backend, middleware, security, rate-limiting]
timestamp: 2026-07-12T00:00:00Z
---

# IP-Based Rate Limiter

In-memory, asyncio-safe rate limiter mounted as Starlette [BaseHTTPMiddleware](https://www.starlette.io/middleware/#basehttpmiddleware) on the [FastAPI Application Layer](/components/api.md). Every inbound request passes through the middleware before reaching route handlers.

## Algorithm

Each client IP gets a single sliding-window bucket:

```
Map<IP, { count: int, expires_at: float }>
```

1. If no bucket exists or the window has expired → create a fresh bucket (`count=1`, `expires_at=now+window`).
2. Otherwise, if `count < max_requests` → increment and allow.
3. Otherwise → reject with HTTP 429 and a `Retry-After` header.

Defaults: **5 requests per 12-hour window**. Configurable via environment variables.

## IP Detection

The client IP is resolved from trusted proxy headers (assumes Caddy in front):

1. `X-Forwarded-For` — first comma-separated value (original client).
2. `X-Real-IP`
3. Socket `client.host` (direct connection fallback).

## Whitelist

A comma-separated list of IPs that bypass rate limiting entirely:

```
RATE_LIMIT_WHITELIST=127.0.0.1,::1
```

## Cleanup

Expired buckets are pruned two ways:
- **Lazily** — on the next access for a given IP, the expired bucket is replaced.
- **Periodically** — a background task (configured via `RATE_LIMIT_CLEANUP_INTERVAL_SECONDS`, default 600 s) runs during the app [lifespan](/components/api.md) and removes all expired entries to bound memory usage.

## Modularity

The `RateLimiter` class exposes only `allow()`, `retry_after()`, and `cleanup()` — callers never touch the internal map. This interface is designed to be swapped for a Redis-backed implementation without changing route handlers or middleware.

## Configuration

| Env Var | Default | Description |
|---|---|---|
| `RATE_LIMIT_ENABLED` | `true` | Master switch; when false, middleware is not registered. |
| `RATE_LIMIT_MAX_REQUESTS` | `5` | Requests allowed per window. |
| `RATE_LIMIT_WINDOW_HOURS` | `12` | Window length in hours. |
| `RATE_LIMIT_WHITELIST` | `""` | Comma-separated IPs to skip. |
| `RATE_LIMIT_CLEANUP_INTERVAL_SECONDS` | `600` | Periodic cleanup interval. |

## Implementation

- `app/ratelimit/__init__.py` — package exports.
- `app/ratelimit/limiter.py` — `RateLimiter` class (in-memory, asyncio.Lock-protected).
- `app/ratelimit/middleware.py` — `RateLimitMiddleware` + `extract_client_ip()`.
