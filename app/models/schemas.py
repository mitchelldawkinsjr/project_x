"""Pydantic models for request validation"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ScrapeRequest(BaseModel):
    """Request model for scraping"""
    source: str = Field(..., min_length=1)
    source_type: str = Field(..., pattern="^(subreddit|user)$")
    limit: int = Field(default=100, ge=1, le=100)
    after: Optional[str] = Field(default=None)
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
