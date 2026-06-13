"""Pydantic models for request/response validation"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class SearchSubredditsResponse(BaseModel):
    """Response model for subreddit search"""
    success: bool
    results: List[dict] = Field(default_factory=list)
    error: Optional[str] = None
    error_type: Optional[str] = None


class MediaItem(BaseModel):
    """Media item model"""
    title: str
    url: str
    author: str
    subreddit: str
    score: int
    permalink: str
    is_video: bool


class ScrapeRequest(BaseModel):
    """Request model for scraping"""
    source: str = Field(..., min_length=1)
    source_type: str = Field(..., pattern="^(subreddit|user)$")
    limit: int = Field(default=100, ge=1, le=100)
    after: Optional[str] = Field(default=None)  # Reddit pagination token
    sort: str = Field(default="hot", pattern="^(hot|top|new|rising)$")
    time_filter: str = Field(default="all", pattern="^(all|year|month|week|day|hour)$")

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value):
        if value is None:
            raise ValueError("source is required")
        text = str(value).strip()
        if not text or text.lower() in ("null", "undefined"):
            raise ValueError("source is required")
        return text

    @field_validator("after", mode="before")
    @classmethod
    def normalize_after(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in ("null", "undefined", "none"):
            return None
        return text


class ScrapeResponse(BaseModel):
    """Response model for scraping"""
    success: bool
    items: List[MediaItem] = Field(default_factory=list)
    count: int = 0
    total: int = 0
    after: Optional[str] = None  # Reddit pagination token for next page
    has_more: bool = False
    error: Optional[str] = None
    error_type: Optional[str] = None

