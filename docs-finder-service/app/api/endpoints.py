import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings
from app.schemas import PaperSearchRequest, PaperSearchResponse, PaperResult
from app.services.search_service import search_papers

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search", response_model=PaperSearchResponse)
async def search(request: PaperSearchRequest):
    """Найти научные публикации по теме и отсортировать по смысловой близости."""
    try:
        results = await run_in_threadpool(
            search_papers,
            query=request.query,
            limit=request.limit,
        )
        return PaperSearchResponse(
            query=request.query,
            model=settings.MODEL_NAME,
            total=len(results),
            results=[PaperResult(**item) for item in results],
        )
    except Exception as exc:
        logger.exception("Paper search failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
