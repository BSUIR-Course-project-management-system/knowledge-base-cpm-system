import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI

from app.api.endpoints import router as api_router
from app.core.config import settings
from app.search_module.src.theme_finder_manager import ThemeFinderManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Search Service...")

    app.state.data_storage_client = httpx.AsyncClient(
        base_url=settings.DATA_STORAGE_URL,
        timeout=30.0,
    )

    manager = ThemeFinderManager()
    app.state.manager = manager

    try:
        manager.init_from_db()
    except Exception as e:
        logger.exception(f"Initialization error: {e}")

    try:
        yield
    finally:
        await app.state.data_storage_client.aclose()
        logger.info("Stopping Search Service...")


app = FastAPI(
    title="Search Microservice",
    description="Search and recommendations service",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router)

if __name__ == "__main__":
    chroma_dir = str(Path(settings.PATH_TO_CHROMA_DB).resolve())

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        reload_dirs=["app"],
        reload_excludes=[
            f"{chroma_dir}/*",
            f"{chroma_dir}/**/*",
            "app/search_module/chroma_db/*",
            "app/search_module/chroma_db/**/*",
        ]
    )