"""Media URL processing service"""
import re
import aiohttp
import asyncio
from typing import Any, Callable, Optional

# Supported image/GIF extensions
MEDIA_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.gifv', '.webp', '.mp4', '.webm'}


def canonical_redgifs_mp4_url(url: str) -> str:
    """
    Map Redgifs watch or media URLs to https://media.redgifs.com/{id}.mp4 using only the URL.

    Note: Redgifs CDN paths are case-sensitive. Watch URLs often use lowercase IDs while
    the CDN file uses mixed case — prefer resolve_redgifs_mp4_url() when post metadata exists.
    """
    if not url or "redgifs.com" not in url.lower():
        return url
    s = url.strip()

    m = re.match(r"https?://media\.redgifs\.com/([^/?#]+)\.(mp4|webm)", s, re.I)
    if m:
        return f"https://media.redgifs.com/{m.group(1)}.mp4"

    m = re.search(r"(?:www\.)?redgifs\.com/watch/([^/?#]+)", s, re.I)
    if m:
        return f"https://media.redgifs.com/{m.group(1)}.mp4"

    return url


def resolve_redgifs_mp4_url(post, url: str) -> str:
    """
    Resolve a playable Redgifs MP4 URL using Reddit oembed metadata when available.

    Redgifs oembed thumbnail_url uses the correct CDN casing, e.g.
    https://media.redgifs.com/JoyfulImmensePug-poster.jpg -> .../JoyfulImmensePug.mp4
    """
    if not url or "redgifs.com" not in url.lower():
        return url

    for attr in ("secure_media", "media"):
        data = getattr(post, attr, None)
        if not data:
            continue
        oembed = data.get("oembed") or {}
        thumb = oembed.get("thumbnail_url") or ""
        poster_match = re.match(
            r"https?://media\.redgifs\.com/([^/?#]+)-poster\.(?:jpg|jpeg|webp|png)",
            thumb,
            re.I,
        )
        if poster_match:
            return f"https://media.redgifs.com/{poster_match.group(1)}.mp4"

        direct_match = re.match(
            r"https?://media\.redgifs\.com/([^/?#]+)\.(mp4|webm)",
            thumb,
            re.I,
        )
        if direct_match:
            return f"https://media.redgifs.com/{direct_match.group(1)}.mp4"

    return canonical_redgifs_mp4_url(url)


async def fetch_redgifs_mp4_from_watch_page(
    url: str,
    http_session: aiohttp.ClientSession,
) -> Optional[str]:
    """Fetch the case-correct Redgifs MP4 URL from a watch page (fallback on 403)."""
    watch_match = re.search(r"(?:www\.)?redgifs\.com/watch/([^/?#]+)", url, re.I)
    media_match = re.search(r"media\.redgifs\.com/([^/?#]+)\.mp4", url, re.I)
    watch_id = watch_match.group(1) if watch_match else (media_match.group(1) if media_match else None)
    if not watch_id:
        return None

    watch_url = f"https://www.redgifs.com/watch/{watch_id}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ),
        "Referer": "https://www.redgifs.com/",
    }
    try:
        async with http_session.get(
            watch_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            if response.status != 200:
                return None
            html = await response.text()

        for pattern in (
            r'property="og:video"\s+content="(https://media\.redgifs\.com/[^"]+\.mp4)"',
            r'"contentUrl":"(https://media\.redgifs\.com/[^"]+\.mp4)"',
            r'(https://media\.redgifs\.com/[A-Za-z0-9_-]+\.mp4)',
        ):
            match = re.search(pattern, html)
            if match:
                candidate = match.group(1)
                if "-poster" not in candidate and "-mobile" not in candidate:
                    if candidate.endswith("-silent.mp4"):
                        candidate = candidate.replace("-silent.mp4", ".mp4")
                    return candidate
    except Exception:
        return None

    return None


def normalize_packaged_reddit_media_url(url: str) -> str:
    """
    packaged-media.redd.it links often include m=DASHPlaylist.mpd (DASH manifest).
    HTML5 <video> cannot play that; drop the DASH selector only and keep auth (e, s, …) params.
    """
    if not url or "packaged-media.redd.it" not in url.lower():
        return url
    try:
        from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

        parts = urlparse(url)
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        filtered = [
            (k, v)
            for k, v in pairs
            if not (
                k.lower() == "m"
                and v
                and ("dashplaylist" in v.lower() or v.lower().endswith(".mpd"))
            )
        ]
        new_q = urlencode(filtered)
        return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_q, parts.fragment))
    except Exception:
        return url


def is_media_url(url: str) -> bool:
    """Check if URL is a direct media link"""
    url_lower = url.lower()
    # Direct media extensions
    if any(url_lower.endswith(ext) for ext in MEDIA_EXTENSIONS):
        return True
    # Reddit image hosting
    if 'i.redd.it' in url_lower:
        return True
    # Imgur direct links
    if 'i.imgur.com' in url_lower or ('imgur.com' in url_lower and '/a/' not in url_lower and '/gallery/' not in url_lower):
        return True
    # Reddit videos (hosted and packaged CDN)
    if 'v.redd.it' in url_lower:
        return True
    if 'packaged-media.redd.it' in url_lower:
        return True
    # Gfycat/Redgifs
    if 'gfycat.com' in url_lower or 'redgifs.com' in url_lower:
        return True
    return False


async def get_redgifs_url(url: str, http_session: aiohttp.ClientSession) -> str:
    """Fetch direct video URL from Redgifs by scraping the page"""
    try:
        # Extract video ID from URL
        match = re.search(r'redgifs\.com/watch/([^/?]+)', url)
        if not match:
            return url
        
        video_id = match.group(1)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            async with http_session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Method 1: Look for JSON-LD structured data
                    json_ld_match = re.search(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
                    if json_ld_match:
                        try:
                            import json
                            json_data = json.loads(json_ld_match.group(1))
                            if isinstance(json_data, dict) and 'contentUrl' in json_data:
                                return json_data['contentUrl']
                        except:
                            pass
                    
                    # Method 2: Look for video source in script tags
                    video_match = re.search(r'"contentUrl"\s*:\s*"([^"]+)"', html)
                    if video_match:
                        video_url = video_match.group(1)
                        if video_url.startswith('http'):
                            return video_url
                    
                    # Method 3: Look for videoUrl
                    video_match = re.search(r'"videoUrl"\s*:\s*"([^"]+)"', html)
                    if video_match:
                        video_url = video_match.group(1)
                        if video_url.startswith('http'):
                            return video_url
                    
                    # Method 4: Look for direct video URLs
                    video_match = re.search(r'(https://[^"]*redgifs[^"]*\.(mp4|webm))', html, re.IGNORECASE)
                    if video_match:
                        video_url = video_match.group(1)
                        if not video_url.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            return video_url
                    
                    # Method 5: Look for thumbs2.redgifs.com pattern
                    video_match = re.search(r'(https://thumbs2\.redgifs\.com/[^"]+\.(mp4|webm))', html, re.IGNORECASE)
                    if video_match:
                        video_url = video_match.group(1)
                        if not video_url.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            return video_url
                    
                    # Method 6: Look for video sources in script tags
                    video_match = re.search(r'"url"\s*:\s*"(https://[^"]*redgifs[^"]*\.(mp4|webm))"', html, re.IGNORECASE)
                    if video_match:
                        video_url = video_match.group(1)
                        if not video_url.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            return video_url
                    
                    # Method 7: Look for media.redgifs.com direct URLs
                    media_match = re.search(r'(https://media\.redgifs\.com/[^"]+\.(mp4|webm))', html, re.IGNORECASE)
                    if media_match:
                        video_url = media_match.group(1)
                        if not video_url.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            return video_url
        except asyncio.TimeoutError:
            return url
        except aiohttp.ClientError:
            return url
        except Exception:
            return url
        
        return url
    except Exception:
        return url


def get_media_url(url: str) -> Optional[str]:
    """Convert various Reddit/Imgur URLs to direct media links"""
    # Handle imgur GIFs
    if 'imgur.com' in url:
        if '/a/' in url or '/gallery/' in url:
            return None  # Albums not supported
        # Try to get direct link
        if url.endswith('.gifv'):
            return url.replace('.gifv', '.mp4')
        if not url.endswith(('.jpg', '.png', '.gif', '.mp4', '.webp')):
            # Try common extensions
            for ext in ['.jpg', '.png', '.gif']:
                test_url = url + ext
                return test_url
    # Handle reddit video / packaged CDN
    if 'v.redd.it' in url or 'packaged-media.redd.it' in url.lower():
        return url
    # Handle gfycat/redgifs - will be processed async
    if 'gfycat.com' in url or 'redgifs.com' in url:
        return url
    return url


def _decode_html_entities(url: str) -> str:
    if "&amp;" in url:
        return url.replace("&amp;", "&")
    return url


def _is_actually_video(media_url: str, is_video: bool) -> bool:
    url_lower = media_url.lower()
    is_reddit_preview_video = "preview.redd.it" in url_lower and (
        "format=mp4" in url_lower or "format=webm" in url_lower
    )
    is_actually_video = (
        is_video
        or any(ext in url_lower for ext in [".mp4", ".webm", ".mov", ".avi"])
        or "v.redd.it" in url_lower
        or "packaged-media.redd.it" in url_lower
        or "media.redgifs.com" in url_lower
        or is_reddit_preview_video
        or (url_lower.endswith(".gif") and "redgifs.com" in url_lower)
        or (
            "redgifs.com" in url_lower
            and ("/watch/" in url_lower or ".mp4" in url_lower or ".webm" in url_lower)
        )
    )
    if (
        not is_reddit_preview_video
        and any(ext in url_lower for ext in [".jpg", ".jpeg", ".png", ".webp"])
        and not is_video
    ):
        is_actually_video = False
    return is_actually_video


def _extract_media_url_from_post_data(post, url: str) -> tuple[Optional[str], bool]:
    """Try Reddit secure_media, media, and preview fields for a direct media URL."""
    media_url = None
    is_video = False

    for attr in ("secure_media", "media"):
        data = getattr(post, attr, None)
        if not data:
            continue
        if "reddit_video" in data:
            media_url = data["reddit_video"].get("fallback_url", url)
            is_video = True
            break
        if "oembed" in data:
            oembed = data.get("oembed", {})
            thumb_url = oembed.get("thumbnail_url", "")
            if thumb_url and (".mp4" in thumb_url.lower() or ".webm" in thumb_url.lower()):
                media_url = thumb_url
                is_video = True
                break
            if thumb_url and "redgifs.com" not in url.lower():
                media_url = thumb_url
                break

    if not media_url and getattr(post, "preview", None):
        images = post.preview.get("images", [])
        if images:
            source = images[0].get("source", {})
            variants = images[0].get("variants", {})
            if "mp4" in variants:
                media_url = variants["mp4"].get("source", {}).get("url", url)
                is_video = True
            elif "gif" in variants:
                media_url = variants["gif"].get("source", {}).get("url", url)
                is_video = True
            else:
                media_url = source.get("url", url)

    return media_url, is_video


def extract_media_from_post(
    post,
    normalize_redgifs: Callable[[str], str],
) -> Optional[dict[str, Any]]:
    """Extract a media item dict from a Reddit post, or None if not media."""
    url = post.url
    try:
        media_url, is_video = _extract_media_url_from_post_data(post, url)
    except Exception:
        media_url, is_video = None, False

    is_redgifs = "redgifs.com" in url.lower()
    if is_redgifs:
        if "media.redgifs.com" in url.lower() and (".mp4" in url.lower() or ".webm" in url.lower()):
            media_url = url
        else:
            media_url = url
        is_video = True
    elif not media_url:
        if is_media_url(url):
            media_url = get_media_url(url)
            if media_url and not is_video:
                is_video = any(
                    x in url.lower()
                    for x in [".mp4", ".webm", "v.redd.it", "packaged-media.redd.it"]
                )
        else:
            return None

    if not media_url:
        return None

    media_url = _decode_html_entities(media_url)
    if "redgifs.com" in media_url.lower():
        media_url = resolve_redgifs_mp4_url(post, media_url)
    else:
        media_url = normalize_redgifs(media_url)
    media_url = normalize_packaged_reddit_media_url(media_url)

    return {
        "title": post.title,
        "url": media_url,
        "author": post.author.name if post.author else "Unknown",
        "subreddit": post.subreddit.display_name,
        "score": post.score,
        "permalink": f"https://reddit.com{post.permalink}",
        "is_video": _is_actually_video(media_url, is_video),
    }

