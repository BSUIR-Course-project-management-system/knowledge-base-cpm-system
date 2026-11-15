from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import StorageDep
from app.schemas import TopicOut, TopicRequest, TopicsPage

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=TopicsPage)
def list_topics(
    params: Annotated[TopicRequest, Query()],
    storage: StorageDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, items = storage.list_topics(params, limit=limit, offset=offset)
    return TopicsPage(total=total, items=items)
