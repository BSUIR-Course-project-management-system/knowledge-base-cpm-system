import logging
import uvicorn

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.endpoints import router as api_router
from app.core.config import settings
from app.search_module.src.loader import JsonLoader
from app.search_module.src.saver import JsonSaver
from app.search_module.src.theme_finder_manager import ThemeFinderManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск Search Service...")

    manager = ThemeFinderManager(loader=JsonLoader(), saver=JsonSaver())
    app.state.manager = manager
    json_path = Path(settings.PATH_TO_TEST_JSON)

    if json_path.exists():
        logger.info(f"Найден тестовый JSON: {json_path}")
        try:
            manager.data_manager = manager.data_manager or __import__(
                'app.search_module.src.data_manager', fromlist=['DataManager']
            ).DataManager(manager.loader)

            manager.data_manager.load(str(json_path))

            logger.info("Инициализация ChromaDB (построение векторов)...")
            manager.prepare_search()
            logger.info("Search Service готов к работе!")
        except Exception as e:
            logger.error(f"Критическая ошибка при инициализации данных: {e}")
    else:
        logger.warning(f"Файл {json_path} не найден! Сервис запущен, но поиск вернет 503.")
        logger.warning("Используйте POST admin/update-data для загрузки данных.")

    yield
    logger.info("Остановка Search Service...")


app = FastAPI(
    title="Search Microservice",
    description="Сервис поиска тем и рекомендаций",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
            host="127.0.0.1",
            port=8001,
            reload=True,
            reload_excludes=["app/search_module/chroma_db/*", "app/search_module/data/*"]
    )
