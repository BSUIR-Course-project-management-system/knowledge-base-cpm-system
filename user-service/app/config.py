from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DB_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TTL: int
    REFRESH_TTl: int


settings = Settings()  # type: ignore
