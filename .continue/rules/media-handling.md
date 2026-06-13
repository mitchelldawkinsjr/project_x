# Media Handling

## Media URL Processing

Media URLs are processed in `app/services/media_service.py`:

### URL Detection (`is_media_url`)
- Checks file extensions
- Checks known media hosting domains
- Returns True if URL is likely a media file

### URL Conversion (`get_media_url`)
- Converts Imgur GIFV to MP4
- Handles Imgur URLs without extensions
- Returns direct media URLs when possible

### Redgifs URL Extraction (`get_redgifs_url`)
- Scrapes Redgifs watch pages to find direct video URLs
- Multiple extraction methods:
  1. JSON-LD structured data
  2. Script tag content URLs
  3. Direct video URL patterns
  4. thumbs2.redgifs.com patterns
- Excludes poster images (`.jpg`, `.png`, etc.)
- Returns original URL if extraction fails (for iframe embedding)

## Video vs Image Detection

### Backend Detection
- Checks Reddit post data for video indicators
- Checks URL extensions (`.mp4`, `.webm`)
- Checks known video domains (`v.redd.it`, `media.redgifs.com`)
- Explicitly excludes image extensions

### Frontend Detection
- Uses `is_video` flag from backend
- Additional URL-based checks
- Distinguishes between:
  - Direct video URLs → `<video>` tag
  - Redgifs watch URLs → `<iframe>` tag
  - Image URLs → `<img>` tag

## Media Display

### Grid View
- Images: `<img>` with lazy loading
- Videos: `<video>` with controls, muted, preload
- Redgifs watch: `<iframe>` (pointerEvents: none)

### Modal View
- Images: Full-size `<img>`
- Videos: `<video>` with autoplay, loop
- Redgifs watch: Full `<iframe>` with allowFullscreen

## CORS Handling

- Direct media URLs (`media.redgifs.com`, `i.redd.it`): No crossOrigin
- External URLs: `crossOrigin = 'anonymous'` for CORS support

## Error Handling

- Video load errors fall back to iframe for Redgifs
- Error messages shown to user
- Console logging for debugging

## Performance

- Lazy loading for images
- Preload metadata for videos
- Caching of extracted Redgifs URLs (24 hour TTL)
- Response compression (GZip)
