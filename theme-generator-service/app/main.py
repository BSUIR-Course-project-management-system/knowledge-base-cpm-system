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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)

@app.get("/", tags=["system"])
async def root():
    return {"service": "project-ideas-service", "docs": "/docs", "health": "/health", "readiness": "/ready"}
