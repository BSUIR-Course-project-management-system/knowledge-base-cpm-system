from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class TopicSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    n_results: int = Field(10, ge=1, le=50)
    max_distance: Optional[float] = Field(
        None, description="Максимальная дистанция (если null - берётся из настроек)"
    )
    is_used: Optional[bool] = False
    examiner: Optional[str] = None
    sort_by: Optional[str] = "relevance"


class InterestsSearchRequest(BaseModel):
    interests: List[str] = Field(..., min_length=1)
    n_results: int = Field(10, ge=1, le=50)
    max_distance: Optional[float] = Field(
        None, description="Максимальная дистанция (если null - берётся из настроек)"
    )
    sort_by: Optional[str] = "relevance"


class SearchResultItem(BaseModel):
    document: str
    distance: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    results: List[SearchResultItem]


class UpdateDataResponse(BaseModel):
    status: str = Field(..., description="success / partial / error")
    message: str = Field(..., description="Текст сообщения")
    updated: int = Field(0, ge=0, description="Количество обноленных записей")


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
