# API Patterns

## FastAPI Route Structure

All API routes follow these patterns:

### Route Decorators
- Use `@app.get()` for GET requests
- Use `@app.post()` for POST requests
- Specify response types: `response_class=JSONResponse` or `HTMLResponse`

### Request Parameters
- Use `Form(...)` for POST form data
- Use query parameters for GET requests
- Use Pydantic models for complex request bodies

### Response Format
- Success responses: `{"success": True, "data": ...}`
- Error responses: `{"success": False, "error": "message"}`
- Always return JSONResponse with consistent structure

### Example Route Pattern

```python
@app.post("/api/scrape")
async def scrape_reddit(
    source: str = Form(...),
    source_type: str = Form(...),
    limit: int = Form(100)
):
    try:
        # Business logic here
        return JSONResponse({
            "success": True,
            "items": media_items,
            "count": len(media_items)
        })
    except Exception as e:
        logger.error(f"Error in scrape_reddit: {e}")
        return JSONResponse({
            "success": False,
            "error": format_error_message(e)
        }, status_code=500)
```

## API Endpoints

### Main Endpoints
- `GET /` - Main page (HTML)
- `GET /api/search-subreddits?q=query` - Subreddit autocomplete search
- `POST /api/scrape` - Scrape Reddit for media
- `GET /api/download?url=...` - Download individual media file
- `POST /api/download/batch` - Batch download as ZIP

### Response Caching
- Subreddit searches: Cached for 1 hour (SUBREDDIT_SEARCH_TTL)
- Media responses: Cached for 30 minutes (MEDIA_RESPONSE_TTL)
- Redgifs URLs: Cached for 24 hours (REDGIFS_URL_TTL)

## Error Handling

- All routes should have try/except blocks
- Use `format_error_message()` utility for user-friendly errors
- Log errors with full context using logger
- Return appropriate HTTP status codes (400, 500, etc.)

## Middleware

- GZip compression for responses > 1000 bytes
- Security headers (X-Content-Type-Options, etc.)
- Process time tracking in response headers
