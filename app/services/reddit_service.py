"""Reddit API service"""
import logging
import re
import praw
from typing import Any, Dict, List, Optional, Tuple

from app.services.media_service import extract_media_from_post

logger = logging.getLogger(__name__)


def _parse_subreddit_names(source: str) -> List[str]:
    """Parse comma or plus separated subreddit names."""
    names = []
    for part in re.split(r"[,+]", source):
        name = part.strip()
        if not name:
            continue
        if name.lower().startswith("r/"):
            name = name[2:]
        names.append(name)
    return names


def _parse_username(source: str) -> str:
    """Normalize a Reddit username (strip u/ prefixes and whitespace)."""
    name = source.strip()
    for prefix in ("/u/", "u/", "/user/", "user/"):
        if name.lower().startswith(prefix):
            name = name[len(prefix):]
            break
    return name.strip()


def _fetch_sorted(listing, sort: str, time_filter: str, limit: int, after: Optional[str]):
    """Return posts from a subreddit or user listing for the given sort mode."""
    params: Dict[str, Any] = {"limit": limit}
    if after:
        params["after"] = after

    if sort == "top":
        return listing.top(time_filter=time_filter, **params)
    if sort == "new":
        return listing.new(**params)
    if sort == "rising":
        return listing.rising(**params)
    return listing.hot(**params)


def _append_subreddit(subreddits: List[Dict[str, Any]], seen_names: set, subreddit) -> None:
    try:
        name = subreddit.display_name.lower()
        if name in seen_names:
            return
        seen_names.add(name)
        subreddits.append({
            "name": subreddit.display_name,
            "subscribers": getattr(subreddit, "subscribers", 0) or 0,
            "description": (getattr(subreddit, "public_description", "") or "")[:100],
        })
    except Exception as e:
        logger.debug("Skipping subreddit result: %s", e)


def initialize_reddit_client(client_id: Optional[str] = None, client_secret: Optional[str] = None) -> praw.Reddit:
    """Initialize Reddit API client"""
    if client_id and client_secret:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="reddit_image_viewer/1.0",
            check_for_updates=False
        )
        logger.info("Reddit API: Authenticated mode")
    else:
        reddit = praw.Reddit(
            client_id=None,
            client_secret=None,
            user_agent="reddit_image_viewer/1.0",
            check_for_updates=False
        )
        logger.warning("Reddit API: Unauthenticated mode (rate limited)")
        logger.warning(
            "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET for better performance"
        )
    return reddit


def search_subreddits(reddit: praw.Reddit, query: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Search for subreddits matching the query"""
    if not query or len(query) < 1:
        return []
    
    subreddits = []
    seen_names = set()
    q_lower = query.lower().strip()
    q_original = query.strip()
    
    search_variations = [q_original, q_lower]
    if len(q_lower) > 2:
        search_variations.extend([
            q_lower + 's',
            q_lower.replace(' ', ''),
            q_lower.replace(' ', '_'),
        ])
    
    try:
        if hasattr(reddit.subreddits, 'search_by_name'):
            for search_term in search_variations[:3]:
                try:
                    for subreddit in reddit.subreddits.search_by_name(search_term, limit=50):
                        _append_subreddit(subreddits, seen_names, subreddit)
                except Exception as e:
                    logger.debug("search_by_name failed for %r: %s", search_term, e)
    except Exception as e:
        logger.debug("search_by_name unavailable: %s", e)
    
    for search_term in [q_lower, q_original]:
        try:
            subreddit = reddit.subreddit(search_term)
            _ = subreddit.display_name
            _append_subreddit(subreddits, seen_names, subreddit)
        except Exception as e:
            logger.debug("Direct subreddit lookup failed for %r: %s", search_term, e)
    
    try:
        for search_term in search_variations[:3]:
            try:
                for subreddit in reddit.subreddits.search(search_term, limit=50):
                    try:
                        name = subreddit.display_name.lower()
                        desc = (getattr(subreddit, "public_description", "") or "").lower()
                        if (q_lower in name or name.startswith(q_lower) or q_lower in desc):
                            _append_subreddit(subreddits, seen_names, subreddit)
                    except Exception as e:
                        logger.debug("Skipping search result: %s", e)
            except Exception as e:
                logger.debug("subreddits.search failed for %r: %s", search_term, e)
    except Exception as e:
        logger.debug("subreddits.search unavailable: %s", e)
    
    def sort_key(x):
        name_lower = x['name'].lower()
        exact_match = name_lower == q_lower
        starts_with = name_lower.startswith(q_lower)
        contains = q_lower in name_lower
        subscribers = x.get('subscribers', 0) or 0
        return (not exact_match, not starts_with, not contains, -subscribers)
    
    subreddits.sort(key=sort_key)
    return subreddits[:limit]


def scrape_media(
    reddit: praw.Reddit,
    source: str,
    source_type: str,
    limit: int,
    after: Optional[str],
    sort: str,
    time_filter: str,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Fetch Reddit posts and extract media items (blocking — run in a thread)."""
    media_items: List[Dict[str, Any]] = []
    next_after: Optional[str] = None

    if source_type == "subreddit":
        subreddit_names = _parse_subreddit_names(source)
        if not subreddit_names:
            return media_items, next_after

        # Reddit supports combined feeds (e.g. pics+aww+gifs) in a single API call.
        combined_source = "+".join(subreddit_names)
        try:
            subreddit = reddit.subreddit(combined_source)
            posts = _fetch_sorted(subreddit, sort, time_filter, limit, after)
            next_after = getattr(posts, "after", None)

            for post in posts:
                item = extract_media_from_post(post)
                if item:
                    media_items.append(item)
        except Exception as e:
            logger.warning("Error processing combined subreddit %s: %s", combined_source, e)
            if len(subreddit_names) == 1:
                raise
            # Fallback: try each subreddit individually if the combined feed fails.
            if len(subreddit_names) > 1:
                per_sub_limit = max(25, limit // len(subreddit_names))
                for subreddit_name in subreddit_names:
                    try:
                        subreddit = reddit.subreddit(subreddit_name)
                        posts = _fetch_sorted(subreddit, sort, time_filter, per_sub_limit, after)
                        next_after = getattr(posts, "after", None)
                        for post in posts:
                            item = extract_media_from_post(post)
                            if item:
                                media_items.append(item)
                    except Exception as inner:
                        logger.warning(
                            "Error processing subreddit %s: %s", subreddit_name, inner
                        )

    elif source_type == "user":
        username = _parse_username(source)
        if not username:
            return media_items, next_after

        user = reddit.redditor(username)
        posts = _fetch_sorted(user.submissions, sort, time_filter, limit, after)
        next_after = getattr(posts, "after", None)

        for post in posts:
            item = extract_media_from_post(post)
            if item:
                media_items.append(item)

    return media_items, next_after
