from typing import Optional

from pydantic import BaseModel, Field


class PaperSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    limit: int = Field(default=10, ge=1, le=30)


class PaperResult(BaseModel):
    title: str
    authors: str
    year: Optional[int] = None
    venue: Optional[str] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    url: str
    relevance: float
    source: str = "OpenAlex"


class PaperSearchResponse(BaseModel):
    query: str
    model: str
    total: int
    results: list[PaperResult]
