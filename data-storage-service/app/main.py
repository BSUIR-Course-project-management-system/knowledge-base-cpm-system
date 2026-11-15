from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import cache, groups, schedule, service, topics
from app.core.exceptions import CacheNotReadyError, RefreshInProgressError
from app.storage_module.storage import StubStorage


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.storage = StubStorage()  # потом: Storage(settings...)
    yield


app = FastAPI(title="Data Storage Service", lifespan=lifespan)


@app.exception_handler(CacheNotReadyError)
async def cache_not_ready(request: Request, exc: CacheNotReadyError):
    return JSONResponse(status_code=503, content={"detail": "Кэш ещё не загружен"})


@app.exception_handler(RefreshInProgressError)
async def refresh_busy(request: Request, exc: RefreshInProgressError):
    return JSONResponse(status_code=409, content={"detail": "Обновление уже идёт"})


for r in (topics.router, schedule.router, groups.router, cache.router, service.router):
    app.include_router(r)
