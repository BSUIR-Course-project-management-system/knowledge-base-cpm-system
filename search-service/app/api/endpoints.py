import json
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.concurrency import run_in_threadpool
from starlette.responses import PlainTextResponse

from app.schemas import (
    TopicSearchRequest,
    ProfileSearchRequest,
    SearchResponse,
    SearchResultItem,
    UpdateDataRequest,
)
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _format_results(raw_results: dict) -> SearchResponse:
    docs = raw_results.get("documents", [[]])[0]
    dists = raw_results.get("distances", [[]])[0]
    metas = raw_results.get("metadatas", [[]])[0]
    items = [
        SearchResultItem(document=d, distance=dist, metadata=m)
        for d, dist, m in zip(docs, dists, metas)
    ]
    return SearchResponse(results=items)


@router.post("/search/topic", response_model=SearchResponse)
async def search_by_topic(request: Request, payload: TopicSearchRequest):
    manager = request.app.state.manager
    if not manager or not manager.theme_finder:
        raise HTTPException(status_code=503, detail="Search engine is not ready")

    md = (
        payload.max_distance
        if payload.max_distance is not None
        else settings.MAX_DISTANCE
    )

    try:
        raw_results = await run_in_threadpool(
            manager.search_relevant,
            query=payload.query,
            n_results=payload.n_results,
            max_distance=md,
            is_used=payload.is_used,
            examiner=payload.examiner,
            sort_by=payload.sort_by,
        )
        return _format_results(raw_results)
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/profile", response_model=SearchResponse)
async def search_by_profile(request: Request, payload: ProfileSearchRequest):
    manager = request.app.state.manager
    if not manager or not manager.theme_finder:
        raise HTTPException(status_code=503, detail="Search engine is not ready")

    query = " ".join(payload.interests)
    md = (
        payload.max_distance
        if payload.max_distance is not None
        else settings.MAX_DISTANCE
    )

    try:
        raw_results = await run_in_threadpool(
            manager.search_relevant,
            query=query,
            n_results=payload.n_results,
            max_distance=md,
            sort_by=payload.sort_by,
        )
        return _format_results(raw_results)
    except Exception as e:
        logger.error(f"Ошибка поиска по профилю: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


#
# @router.post("/admin/update-data")
# async def update_data(request: Request, payload: UpdateDataRequest):
#     manager = request.app.state.manager
#     if not manager:
#         raise HTTPException(status_code=503, detail="Manager is not initialized")
#     try:
#         json_string = json.dumps(payload.data, ensure_ascii=False, indent=2)
#         await run_in_threadpool(
#             manager.process_data_from_json,
#             json_data=json_string,
#             path_to_data=settings.PATH_TO_TEST_JSON,
#         )
#         return {"status": "success", "message": f"Обновлено {len(payload.data)} записей"}
#     except Exception as e:
#         logger.error(f"Ошибка обновления данных: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
