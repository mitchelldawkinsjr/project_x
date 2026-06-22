"""Caching service for API responses"""
from typing import Any, Optional
import time


class CacheService:
    """In-memory cache with optional TTL."""

    def __init__(self):
        self._store: dict[str, tuple[Any, Optional[float]]] = {}

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        expiry = time.time() + ttl_seconds if ttl_seconds else None
        self._store[key] = (value, expiry)

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if expiry is not None and time.time() > expiry:
            del self._store[key]
            return None
        return value

    def get_stats(self) -> dict:
        return {
            "total_entries": len(self._store),
            "entries_with_ttl": sum(1 for _, expiry in self._store.values() if expiry is not None),
        }


cache = CacheService()

SUBREDDIT_SEARCH_TTL = 5 * 60
MEDIA_RESPONSE_TTL = 10 * 60
REDGIFS_URL_TTL = 60 * 60


def build_scrape_cache_key(
    source: str,
    source_type: str,
    limit: int,
    after: Optional[str],
    sort: str,
    time_filter: str,
) -> str:
    after_part = after or "start"
    return (
        f"scrape:{source_type}:{source.lower().strip()}:{limit}:"
        f"{after_part}:{sort}:{time_filter}"
    )
