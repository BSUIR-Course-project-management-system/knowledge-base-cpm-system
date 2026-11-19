from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False)
    app_name: str = "Project Ideas Service"
    llm_provider: str = "ollama"
    llm_base_url: str = "http://ollama:11434"
    llm_model: str = "qwen3:4b"
    llm_temperature: float = 0.6
    llm_timeout: float = 180.0
    llm_max_tokens: int = 1400
    llm_retries: int = 1
    api_port: int = 8000
    cors_origins: list[str] = []

    @property
    def ollama_chat_url(self) -> str:
        return f"{self.llm_base_url.rstrip('/')}/api/chat"

    @property
    def ollama_tags_url(self) -> str:
        return f"{self.llm_base_url.rstrip('/')}/api/tags"

@lru_cache
def get_settings() -> Settings:
    return Settings()
