import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.endpoints import router
from app.services.embedding_service import get_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Docs Finder Service")
    # Загружаем модель при старте, чтобы ошибки модели были видны сразу, а первый пользовательский запрос не ждал её загрузки
    get_model()
    yield
    logger.info("Stopping Docs Finder Service")


app = FastAPI(
    title="Docs Finder Service",
    description="Semantic search for academic papers using OpenAlex and embeddings",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
