from __future__ import annotations

import json
import re
import time
from typing import Any, Optional

import httpx


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers some models add."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


class AsyncLLMClient:
    """Thin async wrapper around any OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(self, base_url: str, api_key: str = "", timeout: float = 120.0):
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        }
        self._timeout = timeout

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str,
        *,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: Optional[dict[str, Any]] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str | dict] = None,
        guided_json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if guided_json:
            payload["guided_json"] = json.dumps(guided_json)

        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/v1/chat/completions",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        data["_latency_ms"] = (time.monotonic() - t0) * 1000

        # Ollama returns empty content when response_format is unsupported.
        # Retry once without it — plain-instruction JSON works fine.
        if (
            response_format
            and not (data["choices"][0]["message"].get("content") or "").strip()
            and not data["choices"][0]["message"].get("tool_calls")
        ):
            payload.pop("response_format", None)
            t0 = time.monotonic()
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    headers=self._headers,
                    json=payload,
                )
                resp.raise_for_status()
            data = resp.json()
            data["_latency_ms"] = (time.monotonic() - t0) * 1000

        return data

    def extract_text(self, response: dict[str, Any]) -> str:
        raw = response["choices"][0]["message"]["content"] or ""
        return _strip_markdown_fences(raw)

    def extract_tool_calls(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        return response["choices"][0]["message"].get("tool_calls") or []

    def extract_usage(self, response: dict[str, Any]) -> int:
        return response.get("usage", {}).get("total_tokens", 0)
