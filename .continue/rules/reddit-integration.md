# Reddit API Integration

## PRAW Client Setup

The Reddit client is initialized in `app/services/reddit_service.py`:

- **Authenticated mode**: Requires `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` env vars
- **Unauthenticated mode**: Works but with strict rate limits
- User agent: `"reddit_image_viewer/1.0"`

## Subreddit Search

The search function (`search_subreddits`) is aggressive and includes:

1. **Multiple search methods**:
   - `search_by_name()` if available (limit: 50)
   - Direct subreddit lookup
   - `subreddits.search()` (limit: 50)
   - Popular subreddits for short queries

2. **Search variations**:
   - Original query, lowercase, plural
   - Searches in both name and description

3. **Search results**:
   - Includes all matching subreddits in results
   - Returns name, subscribers, and description

## Media Scraping

### Post Processing
- Checks `secure_media`, `media`, and `preview` fields for direct video URLs
- Extracts MP4 variants from preview images
- Falls back to URL scraping if Reddit data doesn't have direct links

### Redgifs Handling
- For Redgifs URLs, always fetches actual video (not poster images)
- Scrapes Redgifs page to extract direct MP4 URLs
- Falls back to iframe embedding if direct URL can't be found

### Media URL Detection
Supported media types:
- Direct images: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- Direct videos: `.mp4`, `.webm`
- Reddit hosting: `i.redd.it`, `v.redd.it`
- Imgur: `i.imgur.com`, `imgur.com` (not albums)
- Redgifs: `redgifs.com`, `media.redgifs.com`
- Gfycat: `gfycat.com`

## Rate Limiting

- Authenticated mode: Higher rate limits
- Unauthenticated mode: Strict rate limits (may cause 401 errors)
- Caching helps reduce API calls

## Best Practices

- Always check if subreddit exists before accessing
- Handle `prawcore.exceptions` gracefully
- Use async operations when possible
- Cache subreddit searches aggressively
- Don't use thumbnail URLs for Redgifs (they're poster images)
