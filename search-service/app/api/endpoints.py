import logging

import httpx
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from starlette.responses import PlainTextResponse

from app.core.config import settings
from app.schemas import (
    TopicSearchRequest,
    SearchResponse,
    SearchResultItem, UpdateDataResponse, InterestsSearchRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _format_results(raw_results: dict) -> SearchResponse:
    """Функия форматирования данных"""
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
    """Функция end point для подбора темы по ее тематике"""
    manager = request.app.state.manager
    if not manager or not manager.theme_finder:
        raise HTTPException(status_code=503, detail="Search engine is not ready")

    md = payload.max_distance if payload.max_distance is not None else settings.MAX_DISTANCE
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
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/interests", response_model=SearchResponse)
async def search_by_profile(request: Request, payload: InterestsSearchRequest):
    """Функция end point для подбора темы по ее набору технологий"""
    manager = request.app.state.manager
    if not manager or not manager.theme_finder:
        raise HTTPException(status_code=503, detail="Search engine is not ready")

    query = " ".join(payload.interests)
    md = payload.max_distance if payload.max_distance is not None else settings.MAX_DISTANCE

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
        logger.error(f"Search by interests error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-data", response_model=UpdateDataResponse)
async def update_data(request: Request):
    """Функция end point для обновления данных в ChromaDB"""
    client: httpx.AsyncClient = request.app.state.data_storage_client
    manager = request.app.state.manager

    if not manager:
        raise HTTPException(status_code=503, detail="Manager is not initialized")

    all_items: list[dict] = []
    limit = 100
    offset = 0
    total: int | None = None

    try:
        while True:
            resp = await client.get("/topics", params={"limit": limit, "offset": offset})
            resp.raise_for_status()
            page = resp.json()
            items = page.get("items", [])
            all_items.extend(items)

            if total is None:
                total = page.get("total", 0)

            if len(items) < limit or len(all_items) >= total:
                break
            offset += limit
    except httpx.HTTPStatusError as e:
        logger.error(f"data-storage вернул {e.response.status_code}: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"data-storage error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Не удалось дозвониться до data-storage: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"data-storage unavailable: {e}")

    if not all_items:
        raise HTTPException(status_code=404, detail="data-storage вернул пустой список")

    logger.info(f"Получено {len(all_items)} тем из data-storage")

    try:
        await run_in_threadpool(manager.process_data, data=all_items)
        return UpdateDataResponse(
            status="success",
            message=f"Обновлено {len(all_items)} записей",
            updated=len(all_items),
        )
    except Exception as e:
        logger.error(f"Ошибка перестройки индекса: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics", summary="Получить все темы")
async def get_all_topics(request: Request):
    """Функция end point для получения всех тем и информации о каждой в сыром виде"""
    manager = request.app.state.manager
    if not manager or not manager.data_manager:
        raise HTTPException(status_code=503, detail="Database is not ready")

    return manager.data_manager.collection.get(
        where={"field_type": "topic"},
        include=["documents", "metadatas"]
    )


@router.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    """Функция end point для проверки работоспособности сервиса"""
    return "ok"
