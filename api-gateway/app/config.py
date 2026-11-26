from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    JWT_SECRET: str
    JWT_ALGORITHM: str

    USER_SERVICE_URL: str = "http://user-service:8001"
    SEARCH_SERVICE_URL: str = "http://search-service:8002"
    DATA_STORAGE_SERVICE: str = "http://data-storage-service:8003"
    SCHEDULE_SERVICE: str = "http://schedule-service:8004"
    EXPLANATORY_NOTE_SERVICE_URL: str = "http://explanatory-note-service:8005"
    THEME_GENERATOR_SERVICE: str = "http://theme-generator-service:8006"


settings = Settings()  # type: ignore
