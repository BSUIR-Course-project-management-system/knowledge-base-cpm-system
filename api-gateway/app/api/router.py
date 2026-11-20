from fastapi.routing import APIRouter
from app.api.routers import user_router, search_router

router = APIRouter(prefix="/api")

router.include_router(user_router)
router.include_router(search_router)
