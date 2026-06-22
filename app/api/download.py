"""Download endpoints"""
import io
import logging
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.utils.http_client import get_http_session

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_DOWNLOAD_HOSTS = {
    "i.redd.it",
    "v.redd.it",
    "preview.redd.it",
    "packaged-media.redd.it",
    "external-preview.redd.it",
    "i.imgur.com",
    "imgur.com",
    "media.redgifs.com",
    "thumbs2.redgifs.com",
    "thumbs.redgifs.com",
}


def validate_download_url(url: str) -> None:
    """Reject URLs that could be used for SSRF."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http(s) URLs are allowed")
    host = parsed.netloc.lower().split(":")[0]
    if not any(host == allowed or host.endswith(f".{allowed}") for allowed in ALLOWED_DOWNLOAD_HOSTS):
        raise HTTPException(status_code=400, detail="URL host is not allowed for download")


async def download_file(url: str) -> bytes:
    """Download a file from URL using the shared HTTP session."""
    validate_download_url(url)
    session = await get_http_session()
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            raise HTTPException(
                status_code=response.status,
                detail=f"Failed to download: {response.status}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")


@router.get("/api/download")
async def download_single(url: str):
    """Download a single media file."""
    try:
        file_data = await download_file(url)

        filename = url.split("/")[-1].split("?")[0]
        if not filename or "." not in filename:
            filename = "media_file"

        return StreamingResponse(
            io.BytesIO(file_data),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
