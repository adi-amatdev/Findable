"""Thin async wrapper around the Firecrawl scrape API."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from .config import Settings


class FirecrawlError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class FirecrawlClient:
    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.firecrawl_api_key}",
            "Content-Type": "application/json",
        }

    async def scrape(self, url: str, options: dict[str, Any]) -> dict[str, Any]:
        """POST {url, ...options} to Firecrawl and return the `data` object."""
        if not self._settings.firecrawl_api_key:
            raise FirecrawlError("FIRECRAWL_API_KEY is not configured.", status_code=500)

        payload = {"url": url, **options}
        try:
            async with httpx.AsyncClient(timeout=self._settings.firecrawl_timeout) as client:
                resp = await client.post(
                    self._settings.scrape_endpoint,
                    json=payload,
                    headers=self._headers,
                )
        except httpx.HTTPError as exc:
            raise FirecrawlError(f"Could not reach Firecrawl: {exc}", status_code=502) from exc

        body = _safe_json(resp)
        if resp.status_code >= 400:
            raise FirecrawlError(
                f"Firecrawl returned HTTP {resp.status_code}.",
                status_code=resp.status_code,
                payload=body,
            )
        if isinstance(body, dict) and body.get("success") is False:
            raise FirecrawlError(
                body.get("error", "Firecrawl request failed."),
                status_code=502,
                payload=body,
            )
        # v1/v2 wrap the useful bits under `data`; fall back to the whole body.
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {"raw": body}


def _safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}
