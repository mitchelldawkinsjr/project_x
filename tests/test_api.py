"""API endpoint tests"""
from app.services.cache_service import build_scrape_cache_key


def test_home_page(client):
    """Test home page loads"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "/static/css/style.css" in response.text
    assert "/static/js/app.js" in response.text


def test_static_assets(client):
    """Test static CSS and JS are served"""
    css = client.get("/static/css/style.css")
    js = client.get("/static/js/app.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert "javascript" in js.headers["content-type"]


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "cache_stats" in data


def test_search_subreddits_empty(client):
    """Test subreddit search with empty query"""
    response = client.get("/api/search-subreddits?q=")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["results"], list)


def test_search_subreddits_invalid(client):
    """Test subreddit search with invalid query"""
    response = client.get("/api/search-subreddits?q=invalid_subreddit_xyz123")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["results"], list)


def test_proxy_video_rejects_non_redgifs(client):
    """Test video proxy only allows Redgifs URLs"""
    response = client.get("/api/proxy-video?url=https://example.com/video.mp4")
    assert response.status_code == 400
    assert "Only Redgifs URLs are allowed" in response.json()["error"]


def test_download_rejects_invalid_host(client):
    """Test download endpoint blocks SSRF-prone URLs"""
    response = client.get("/api/download?url=https://example.com/secret.txt")
    assert response.status_code == 400


def test_download_batch_rejects_empty_list(client):
    """Test batch download requires at least one URL"""
    response = client.post("/api/download-batch", json=[])
    assert response.status_code == 422


def test_download_batch_rejects_invalid_host(client):
    """Test batch download validates each URL host"""
    response = client.post(
        "/api/download-batch",
        json=["https://example.com/image.jpg"],
    )
    assert response.status_code == 400


def test_scrape_cache_key_is_deterministic():
    """Test scrape cache keys are stable for identical requests"""
    key_a = build_scrape_cache_key("pics", "subreddit", 25, None, "hot", "all")
    key_b = build_scrape_cache_key("pics", "subreddit", 25, None, "hot", "all")
    key_c = build_scrape_cache_key("pics", "subreddit", 25, "t3_abc", "hot", "all")
    assert key_a == key_b
    assert key_a != key_c

