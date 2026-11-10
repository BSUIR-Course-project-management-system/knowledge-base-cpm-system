from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class TopicSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    n_results: int = Field(10, ge=1, le=50)
    max_distance: Optional[float] = Field(None, description="Максимальная дистанция (если null — берётся из настроек)")
    is_used: Optional[bool] = False
    проверяющий: Optional[str] = None
    sort_by: Optional[str] = "relevance"


class ProfileSearchRequest(BaseModel):
    interests: List[str] = Field(..., min_length=1)
    n_results: int = Field(10, ge=1, le=50)
    max_distance: Optional[float] = Field(None, description="Максимальная дистанция (если null — берётся из настроек)")
    sort_by: Optional[str] = "relevance"


class SearchResultItem(BaseModel):
    document: str
    distance: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    results: List[SearchResultItem]


class UpdateDataRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(...)