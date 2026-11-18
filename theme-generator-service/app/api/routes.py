from fastapi import APIRouter, HTTPException
from app.config import get_settings
from app.schemas import GenerateIdeasRequest, GenerateIdeasResponse
from app.services.idea_generator import IdeaGenerator

router = APIRouter()
settings = get_settings()
generator = IdeaGenerator(settings)

@router.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}

@router.get("/ready", tags=["system"])
async def ready():
    if not await generator.client.is_available():
        raise HTTPException(status_code=503, detail={
            "status": "not_ready",
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "message": "Ollama недоступна или модель ещё не загружена.",
        })
    return {"status": "ready", "provider": settings.llm_provider, "model": settings.llm_model}

@router.post("/generate", response_model=GenerateIdeasResponse, tags=["ideas"], summary="Сгенерировать 5 идей курсовых IT-проектов")
async def generate_ideas(request: GenerateIdeasRequest):
    try:
        return await generator.generate(request.subject_area)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Не удалось получить корректный ответ от языковой модели: {type(exc).__name__}. Проверьте /ready и журналы Docker.",
        ) from exc
