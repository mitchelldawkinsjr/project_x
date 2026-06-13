from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError
import os
import asyncio
import time
from dotenv import load_dotenv

from app.services.reddit_service import initialize_reddit_client, search_subreddits, scrape_media
from app.services.media_service import (
    canonical_redgifs_mp4_url,
    extract_media_from_post,
    fetch_redgifs_mp4_from_watch_page,
)
from app.services.cache_service import (
    cache,
    SUBREDDIT_SEARCH_TTL,
    MEDIA_RESPONSE_TTL,
    REDGIFS_URL_TTL,
    build_scrape_cache_key,
)
from app.utils.helpers import format_error_message
from app.utils.http_client import close_http_session, get_http_session
from app.utils.logger import get_logger

try:
    from app.api.download import router as download_router
except ImportError:
    download_router = None

logger = get_logger()

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_http_session()


app = FastAPI(title="Reddit Image/GIF Viewer", lifespan=lifespan)

if download_router:
    app.include_router(download_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

if os.getenv("TESTING") != "1":
    app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


client_id = os.getenv("REDDIT_CLIENT_ID", "")
client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
reddit = initialize_reddit_client(client_id, client_secret)

templates = Jinja2Templates(directory="templates")


def normalize_redgifs_item_url(media_url: str) -> str:
    """Map Redgifs URLs to canonical MP4 URLs with caching."""
    if not media_url or "redgifs.com" not in media_url.lower():
        return media_url
    out = canonical_redgifs_mp4_url(media_url)
    if out == media_url:
        return media_url
    cache_key = f"redgifs_mp4:{media_url}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    cache.set(cache_key, out, REDGIFS_URL_TTL)
    return out


def _extract_post_with_normalizer(post):
    return extract_media_from_post(post, normalize_redgifs_item_url)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "cache_stats": cache.get_stats(),
    })


@app.get("/api/proxy-video")
async def proxy_video(request: Request, url: str):
    """Proxy video requests with proper headers to bypass CORS/403 restrictions."""
    from urllib.parse import urlparse

    parsed_url = urlparse(url)
    if "redgifs.com" not in parsed_url.netloc.lower():
        return JSONResponse({"error": "Only Redgifs URLs are allowed"}, status_code=400)

    try:
        session = await get_http_session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Referer": "https://www.redgifs.com/",
            "Accept": (
                "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,"
                "audio/*;q=0.6,*/*;q=0.5"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        range_header = request.headers.get("Range")
        if range_header:
            headers["Range"] = range_header

        upstream = await session.get(url, headers=headers, allow_redirects=True)
        if upstream.status == 403 and "media.redgifs.com" in url.lower():
            resolved = await fetch_redgifs_mp4_from_watch_page(url, session)
            if resolved and resolved != url:
                upstream.release()
                url = resolved
                upstream = await session.get(url, headers=headers, allow_redirects=True)

        if upstream.status not in (200, 206):
            upstream.release()
            return JSONResponse(
                {"error": f"Failed to fetch video: {upstream.status}", "status": upstream.status},
                status_code=upstream.status,
            )

        response_headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
            "Content-Type": upstream.headers.get("Content-Type", "video/mp4"),
        }
        content_length = upstream.headers.get("Content-Length")
        if content_length:
            response_headers["Content-Length"] = content_length
        if "Content-Range" in upstream.headers:
            response_headers["Content-Range"] = upstream.headers["Content-Range"]

        async def stream_chunks():
            try:
                async for chunk in upstream.content.iter_chunked(65536):
                    yield chunk
            finally:
                upstream.release()

        return StreamingResponse(
            stream_chunks(),
            status_code=upstream.status,
            media_type=upstream.headers.get("Content-Type", "video/mp4"),
            headers=response_headers,
        )
    except Exception as e:
        logger.error("Error proxying video %s: %s", url, e, exc_info=True)
        return JSONResponse({"error": f"Failed to proxy video: {str(e)}"}, status_code=500)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/search-subreddits")
async def search_subreddits_endpoint(q: str):
    """Search for subreddits matching the query."""
    try:
        if not q or len(q) < 1:
            return JSONResponse({"success": True, "results": []})

        cache_key = f"subreddit_search_{q.lower().strip()}"
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            logger.info("Cache hit for subreddit search: %s", q)
            return JSONResponse({"success": True, "results": cached_results})

        results = await asyncio.to_thread(search_subreddits, reddit, q, 30)
        cache.set(cache_key, results, SUBREDDIT_SEARCH_TTL)

        return JSONResponse({"success": True, "results": results})
    except Exception as e:
        logger.error("Error searching subreddits: %s", e, exc_info=True)
        error_info = format_error_message(e)
        return JSONResponse(
            {
                "success": False,
                "error": error_info["error"],
                "error_type": error_info["error_type"],
            },
            status_code=error_info["status_code"],
        )


@app.post("/api/scrape")
async def scrape_reddit(
    source: str = Form(...),
    source_type: str = Form(...),
    limit: int = Form(100),
    after: str = Form(None),
    sort: str = Form("hot"),
    time_filter: str = Form("all"),
):
    """Scrape Reddit for images and GIFs."""
    try:
        from app.models.schemas import ScrapeRequest

        try:
            request_data = ScrapeRequest(
                source=source,
                source_type=source_type,
                limit=limit,
                after=after,
                sort=sort,
                time_filter=time_filter,
            )
        except ValidationError as e:
            logger.warning("Validation error: %s", e)
            return JSONResponse(
                {
                    "success": False,
                    "error": f"Invalid request parameters: {str(e)}",
                    "error_type": "validation_error",
                },
                status_code=400,
            )

        cache_key = build_scrape_cache_key(
            request_data.source,
            request_data.source_type,
            request_data.limit,
            request_data.after,
            request_data.sort,
            request_data.time_filter,
        )
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            logger.info("Cache hit for scrape: %s", request_data.source)
            return JSONResponse(cached_response)

        media_items, next_after = await asyncio.to_thread(
            scrape_media,
            reddit,
            request_data.source,
            request_data.source_type,
            request_data.limit,
            request_data.after,
            request_data.sort,
            request_data.time_filter,
            _extract_post_with_normalizer,
        )

        response_data = {
            "success": True,
            "items": media_items,
            "count": len(media_items),
            "total": len(media_items),
            "after": next_after,
            "has_more": next_after is not None,
        }
        cache.set(cache_key, response_data, MEDIA_RESPONSE_TTL)

        return JSONResponse(response_data)

    except Exception as e:
        logger.error("Error scraping Reddit: %s", e, exc_info=True)
        error_info = format_error_message(e)
        return JSONResponse(
            {
                "success": False,
                "error": error_info["error"],
                "error_type": error_info["error_type"],
            },
            status_code=error_info["status_code"],
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3005)
