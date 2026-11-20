from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    JWT_SECRET: str
    JWT_ALGORITHM: str

    USER_SERVICE_URL: str = "http://user-service:8001"
    SEARCH_SERVICE_URL: str = "http://search-service:8002"


settings = Settings()  # type: ignore
