"""Service layer tests"""
import pytest
from pydantic import ValidationError
from app.models.schemas import ScrapeRequest
from app.services.cache_service import CacheService
from app.services.reddit_service import _parse_subreddit_names, _parse_username
from app.services.media_service import (
    is_media_url,
    get_media_url,
    canonical_redgifs_mp4_url,
    extract_redgifs_id,
    normalize_packaged_reddit_media_url,
    resolve_redgifs_mp4_url,
)


def test_parse_username_strips_prefixes():
    assert _parse_username("spez") == "spez"
    assert _parse_username("u/spez") == "spez"
    assert _parse_username("/u/spez") == "spez"
    assert _parse_username("  U/Spez  ") == "Spez"
    assert _parse_username("user/spez") == "spez"


def test_parse_subreddit_names_strips_r_prefix():
    assert _parse_subreddit_names("pics,aww") == ["pics", "aww"]
    assert _parse_subreddit_names("r/pics+r/aww") == ["pics", "aww"]


def test_scrape_request_normalizes_after_sentinels():
    request = ScrapeRequest(
        source="pics",
        source_type="subreddit",
        after="null",
    )
    assert request.after is None

    request = ScrapeRequest(
        source="pics",
        source_type="subreddit",
        after="t3_abc123",
    )
    assert request.after == "t3_abc123"


def test_scrape_request_rejects_blank_source():
    with pytest.raises(ValidationError):
        ScrapeRequest(source="   ", source_type="subreddit")


def test_canonical_redgifs_mp4_url():
    assert canonical_redgifs_mp4_url("https://www.redgifs.com/watch/foo-bar") == (
        "https://media.redgifs.com/foo-bar.mp4"
    )
    assert canonical_redgifs_mp4_url("https://media.redgifs.com/foo-bar.webm") == (
        "https://media.redgifs.com/foo-bar.mp4"
    )
    assert canonical_redgifs_mp4_url("https://media.redgifs.com/foo-bar.mp4") == (
        "https://media.redgifs.com/foo-bar.mp4"
    )
    assert canonical_redgifs_mp4_url("https://i.redd.it/x.jpg") == "https://i.redd.it/x.jpg"


def test_extract_redgifs_id():
    assert extract_redgifs_id("https://www.redgifs.com/watch/foo-bar") == "foo-bar"
    assert extract_redgifs_id("https://media.redgifs.com/FooBar.mp4") == "FooBar"
    assert extract_redgifs_id("https://media.redgifs.com/FooBar-silent.mp4") == "FooBar"
    assert extract_redgifs_id("https://i.redd.it/x.jpg") is None


def test_resolve_redgifs_mp4_url_uses_poster_casing():
    class FakePost:
        url = "https://www.redgifs.com/watch/joyfulimmensepug"
        secure_media = {
            "oembed": {
                "thumbnail_url": "https://media.redgifs.com/JoyfulImmensePug-poster.jpg",
            }
        }
        media = secure_media

    resolved = resolve_redgifs_mp4_url(
        FakePost(),
        "https://www.redgifs.com/watch/joyfulimmensepug",
    )
    assert resolved == "https://media.redgifs.com/JoyfulImmensePug.mp4"


def test_cache_service():
    """Test cache service"""
    test_cache = CacheService()

    test_cache.set("test_key", "test_value")
    assert test_cache.get("test_key") == "test_value"

    test_cache.set("ttl_key", "ttl_value", ttl_seconds=1)
    assert test_cache.get("ttl_key") == "ttl_value"
    assert test_cache.get("missing_key") is None


def test_normalize_packaged_reddit_media_url():
    u = (
        "https://packaged-media.redd.it/x/pb/m2-res_854p.mp4?"
        "m=DASHPlaylist.mpd&var=sgpssan&v=1&e=1779411600&s=deadbeef"
    )
    out = normalize_packaged_reddit_media_url(u)
    assert "DASHPlaylist" not in out
    assert "e=1779411600" in out and "s=deadbeef" in out
    assert "packaged-media.redd.it" in out


def test_is_media_url():
    """Test media URL detection"""
    assert is_media_url("https://i.redd.it/image.jpg") is True
    assert is_media_url("https://example.com/image.png") is True
    assert is_media_url("https://packaged-media.redd.it/x/y/z.mp4?m=DASHPlaylist.mpd") is True
    assert is_media_url("https://redgifs.com/watch/video") is True
    assert is_media_url("https://example.com/page.html") is False


def test_get_media_url():
    """Test media URL conversion"""
    # Test imgur GIFV
    url = get_media_url("https://imgur.com/image.gifv")
    assert url == "https://imgur.com/image.mp4"
    
    # Test reddit video
    url = get_media_url("https://v.redd.it/video")
    assert url == "https://v.redd.it/video"

