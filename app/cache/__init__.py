"""Redis cache for crawl/pipeline results."""

from .store import Cache, get_cache, make_key

__all__ = ["Cache", "get_cache", "make_key"]
