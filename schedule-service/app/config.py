from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    WORK_START_HOUR: int = 15
    WORK_END_HOUR: int = 19
    STEP_MINUTES: int = 30

    DATA_STORAGE_URL: str = "http://data-storage-service:8003"


settings = Settings()  # type: ignore
