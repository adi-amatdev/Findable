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
    # Comma-separated list of allowed CORS origins, or "*" for all.
    cors_origins: str = "*"

    # --- Firecrawl ---
    firecrawl_api_key: str = ""
    firecrawl_api_url: str = "https://api.firecrawl.dev"
    firecrawl_api_version: str = "v2"
    firecrawl_timeout: float = 60.0

    # --- Redis cache ---
    redis_url: str = "redis://localhost:6379/0"
    cache_enabled: bool = True
    # TTL for cached scrapes, in seconds. 0 = never expire (cache forever).
    cache_ttl_seconds: int = 604800  # 7 days

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
