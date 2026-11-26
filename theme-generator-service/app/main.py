from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.config import get_settings

settings = get_settings()
app = FastAPI(
    title="Project Ideas Service",
    description="Локальный микросервис генерации идей IT-курсовых проектов.",
    version="1.0.0",
)

app.include_router(router)
