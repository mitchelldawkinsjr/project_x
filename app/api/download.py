"""Download endpoints"""
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
from urllib.parse import urlparse
import zipfile
import io

from app.utils.http_client import get_http_session
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("download")

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


@router.post("/api/download-batch")
async def download_batch(urls: List[str] = Body(..., min_length=1, max_length=50)):
    """Download multiple files as a ZIP."""
    try:
        zip_buffer = io.BytesIO()
        downloaded = 0

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, url in enumerate(urls):
                try:
                    file_data = await download_file(url)
                    filename = url.split("/")[-1].split("?")[0]
                    if not filename or "." not in filename:
                        filename = f"media_{i + 1}"
                    zip_file.writestr(filename, file_data)
                    downloaded += 1
                except HTTPException as e:
                    logger.warning("Skipping download for %s: %s", url, e.detail)
                except Exception as e:
                    logger.warning("Skipping download for %s: %s", url, e)

        if downloaded == 0:
            raise HTTPException(status_code=400, detail="No files could be downloaded")

        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=reddit_media.zip"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
