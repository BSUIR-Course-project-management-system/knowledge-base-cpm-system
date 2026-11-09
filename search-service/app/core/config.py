from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent.parent
MODULE_DIR = BASE_DIR / "app" / "search_module"


class Settings(BaseSettings):
    PATH_TO_CHROMA_DB: str = str(MODULE_DIR / "chroma_db")
    PATH_TO_TEST_JSON: str = str(MODULE_DIR / "data" / "data.json")
    PATH_TO_MODEL: str = str(MODULE_DIR / "models" / "model")
    MAX_DISTANCE: float = 1.1
    MODEL_NAME: str = "BAAI/bge-m3"

    class Config:
        env_file = ".env"


settings = Settings()