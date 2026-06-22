from contextlib import asynccontextmanager
import asyncio
import logging
import os
import time
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.api.download import router as download_router
from app.services.cache_service import (
    MEDIA_RESPONSE_TTL,
    REDGIFS_URL_TTL,
    SUBREDDIT_SEARCH_TTL,
    build_scrape_cache_key,
    cache,
)
from app.services.media_service import extract_redgifs_id, fetch_redgifs_mp4_from_watch_page
from app.services.reddit_service import initialize_reddit_client, scrape_media, search_subreddits
from app.utils.helpers import format_error_message
from app.utils.http_client import close_http_session, get_http_session

logger = logging.getLogger(__name__)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_http_session()


app = FastAPI(title="Reddit Image/GIF Viewer", lifespan=lifespan)
app.include_router(download_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

if os.getenv("TESTING") != "1":
    app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start_time)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


client_id = os.getenv("REDDIT_CLIENT_ID", "")
client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
reddit = initialize_reddit_client(client_id, client_secret)

templates = Jinja2Templates(directory="templates")


async def _resolve_redgifs_play_url(url: str, session) -> str:
    """Resolve case-correct Redgifs MP4 URL via watch page, with cache."""
    cache_key = f"redgifs_resolved:{url.strip().lower()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    resolved = await fetch_redgifs_mp4_from_watch_page(url, session)
    if resolved:
        cache.set(cache_key, resolved, REDGIFS_URL_TTL)
        return resolved
    return url


@app.get("/health")
async def health_check():
    return JSONResponse({
        "status": "healthy",
        "cache_stats": cache.get_stats(),
    })


@app.get("/api/resolve-redgifs")
async def resolve_redgifs(url: str):
    if not url or "redgifs.com" not in url.lower():
        return JSONResponse({"error": "Only Redgifs URLs are allowed"}, status_code=400)

    session = await get_http_session()
    resolved = await _resolve_redgifs_play_url(url, session)
    watch_id = extract_redgifs_id(resolved or url)
    if not watch_id:
        return JSONResponse({"error": "Could not parse Redgifs URL"}, status_code=400)

    return JSONResponse({
        "url": resolved,
        "watch_id": watch_id,
        "embed_url": f"https://www.redgifs.com/ifr/{watch_id.lower()}",
    })


@app.get("/api/proxy-video")
async def proxy_video(request: Request, url: str):
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

        original_url = url.strip()
        url = await _resolve_redgifs_play_url(original_url, session)
        upstream = await session.get(url, headers=headers, allow_redirects=True)
        content_type = (upstream.headers.get("Content-Type") or "").lower()
        if upstream.status in (403, 404) or (
            upstream.status in (200, 206) and content_type and not content_type.startswith("video/")
        ):
            resolved = await fetch_redgifs_mp4_from_watch_page(url, session)
            if resolved and resolved != url:
                upstream.release()
                url = resolved
                cache.set(f"redgifs_resolved:{original_url.lower()}", resolved, REDGIFS_URL_TTL)
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
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/search-subreddits")
async def search_subreddits_endpoint(q: str):
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
        )

        response_data = {
            "success": True,
            "items": media_items,
            "count": len(media_items),
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
