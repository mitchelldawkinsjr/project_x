# API Documentation

## Endpoints

### GET `/`
Main page - serves the HTML interface.

**Response**: HTML page

---

### GET `/health`
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "cache_stats": {
    "total_entries": 0,
    "entries_with_ttl": 0,
    "cache_keys": []
  }
}
```

---

### GET `/api/search-subreddits`
Search for subreddits matching a query.

**Query Parameters**:
- `q` (string, required): Search query (minimum 1 character)

**Response**:
```json
{
  "success": true,
  "results": [
    {
      "name": "subreddit_name",
      "subscribers": 12345,
      "description": "Subreddit description"
    }
  ]
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Error message",
  "error_type": "api_error"
}
```

---

### POST `/api/scrape`
Scrape Reddit for media items.

**Form Data**:
- `source` (string, required): Subreddit name(s) or username (comma-separated)
- `source_type` (string, required): Either "subreddit" or "user"
- `limit` (int, optional, default=100): Number of items to fetch per page (1-100)
- `after` (string, optional): Reddit pagination token for the next page
- `sort` (string, optional, default="hot"): Sort order - "hot", "top", "new", or "rising"
- `time_filter` (string, optional, default="all"): Time filter for "top" sort - "all", "year", "month", "week", "day", "hour"

**Response**:
```json
{
  "success": true,
  "items": [
    {
      "title": "Post title",
      "url": "https://media.url",
      "author": "username",
      "subreddit": "subreddit_name",
      "score": 1234,
      "permalink": "https://reddit.com/r/subreddit/comments/...",
      "is_video": false
    }
  ],
  "count": 25,
  "after": "t3_abc123",
  "has_more": true
}
```

---

### GET `/api/download`
Download a single media file.

**Query Parameters**:
- `url` (string, required): URL of the media file to download

**Response**: Binary file download

---

## Error Types

- `api_error`: General API error
- `rate_limit_error`: Rate limit exceeded
- `validation_error`: Invalid request parameters
- `timeout_error`: Request timed out

## Rate Limiting

The API uses caching to reduce load:
- Subreddit search results: 5 minutes TTL
- Media responses: 10 minutes TTL
- Redgifs URL resolutions: 1 hour TTL

