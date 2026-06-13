"""Caching service for API responses"""
from typing import Any, Optional
import time


class CacheService:
    """In-memory cache service with TTL support"""
    
    def __init__(self):
        self._cache: dict = {}
        self._ttl: dict = {}
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set a cache value with optional TTL"""
        self._cache[key] = value
        if ttl_seconds:
            self._ttl[key] = time.time() + ttl_seconds
        elif key in self._ttl:
            del self._ttl[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get a cache value if it exists and hasn't expired"""
        if key not in self._cache:
            return None
        
        # Check TTL
        if key in self._ttl:
            if time.time() > self._ttl[key]:
                # Expired
                del self._cache[key]
                del self._ttl[key]
                return None
        
        return self._cache[key]
    
    def delete(self, key: str) -> None:
        """Delete a cache entry"""
        if key in self._cache:
            del self._cache[key]
        if key in self._ttl:
            del self._ttl[key]
    
    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
        self._ttl.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "total_entries": len(self._cache),
            "entries_with_ttl": len(self._ttl),
            "cache_keys": list(self._cache.keys())
        }


# Global cache instance
cache = CacheService()

# Cache TTL constants (in seconds)
SUBREDDIT_SEARCH_TTL = 5 * 60  # 5 minutes
MEDIA_RESPONSE_TTL = 10 * 60  # 10 minutes
REDGIFS_URL_TTL = 60 * 60  # 1 hour


def build_scrape_cache_key(
    source: str,
    source_type: str,
    limit: int,
    after: Optional[str],
    sort: str,
    time_filter: str,
) -> str:
    """Build a deterministic cache key for scrape requests."""
    after_part = after or "start"
    return (
        f"scrape:{source_type}:{source.lower().strip()}:{limit}:"
        f"{after_part}:{sort}:{time_filter}"
    )

