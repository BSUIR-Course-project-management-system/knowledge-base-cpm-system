from fastapi.routing import APIRouter
from app.schemas import StudentRegistrationSchema, TokenResponseSchema
from app.api_client import request_service
from app.config import settings

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register/students")
async def register_student(schema: StudentRegistrationSchema) -> TokenResponseSchema:
    return await request_service(
        "POST",
        f"{settings.USER_SERVICE_URL}/auth/register/student",
        body=schema.model_dump(),
    )
