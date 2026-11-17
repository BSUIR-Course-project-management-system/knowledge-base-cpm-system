from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки научного поискового микросервиса."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    OPENALEX_BASE_URL: str = "https://api.openalex.org/works"
    OPENALEX_MAILTO: str = ""
    OPENALEX_TIMEOUT: float = 25.0
    OPENALEX_RETRIES: int = 2

    MODEL_NAME: str = "BAAI/bge-m3"
    HF_HOME: str = "/models"

    CANDIDATE_LIMIT: int = 50


settings = Settings()
