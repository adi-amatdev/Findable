"""Application configuration, loaded from environment / .env file."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Field names map to UPPER_CASE env vars.

    e.g. `firecrawl_api_key` <- `FIRECRAWL_API_KEY`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App / HTTP server ---
    app_name: str = "Findable"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = True
    log_level: str = "info"
    cors_origins: str = "*"  # comma-separated, or "*"

    # --- Firecrawl (rendered crawl) ---
    firecrawl_api_key: str = ""
    firecrawl_api_url: str = "https://api.firecrawl.dev"
    firecrawl_api_version: str = "v2"
    firecrawl_timeout: float = 60.0

    # --- Direct fetch (raw HTML, robots.txt, sitemap.xml, llms.txt) ---
    fetch_timeout: float = 20.0
    fetch_user_agent: str = "FindableBot/0.1 (+https://findable.ai)"

    # --- Redis cache ---
    redis_url: str = "redis://localhost:6379/0"
    cache_enabled: bool = True
    cache_ttl_seconds: int = 604800  # 7 days; 0 = never expire

    # --- LLM / Model Router ---
    # Master switch. When false, agents run in deterministic heuristic mode
    # (no external model calls) - the whole audit still runs end-to-end.
    llm_enabled: bool = False
    llm_timeout: float = 60.0
    # Local vLLM (OpenAI-compatible). In docker-compose this points at the
    # vllm service; leave blank to disable the local backend.
    vllm_base_url: str = ""
    vllm_api_key: str = "EMPTY"
    # Remote Fireworks (OpenAI-compatible) for the two heaviest roles.
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"
    fireworks_api_key: str = ""

    # --- Agents SEO Core (inference layer) ---
    # URL of the agents-api service. In docker-compose this is http://agents-api:8080.
    # Leave blank to disable forwarding (sitefacts-only mode).
    agents_url: str = "http://localhost:8080"

    # --- Mock stream (dev / frontend testing) ---
    # When true: POST /api/audit/start skips Firecrawl and agents entirely.
    # A static SiteFacts + static AuditReport are used. Real SSE events are
    # still emitted on a realistic schedule so the frontend streaming UI can
    # be built and tested without burning any API credits.
    mock_stream: bool = False

    # --- Orchestrator scope ---
    max_deep_pages: int = 4    # follow-up pages that get the full 4-agent pass
    max_shallow_pages: int = 50  # ceiling on the deterministic site crawl

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def scrape_endpoint(self) -> str:
        base = self.firecrawl_api_url.rstrip("/")
        return f"{base}/{self.firecrawl_api_version}/scrape"


@lru_cache
def get_settings() -> Settings:
    return Settings()
