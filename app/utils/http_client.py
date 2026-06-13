"""Shared aiohttp client session with connection pooling."""
from typing import Optional

import aiohttp

_http_session: Optional[aiohttp.ClientSession] = None


async def get_http_session() -> aiohttp.ClientSession:
    """Get or create shared aiohttp session with connection pooling."""
    global _http_session
    if _http_session is None or _http_session.closed:
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        _http_session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30),
        )
    return _http_session


async def close_http_session() -> None:
    """Close the shared session on application shutdown."""
    global _http_session
    if _http_session and not _http_session.closed:
        await _http_session.close()
        _http_session = None
