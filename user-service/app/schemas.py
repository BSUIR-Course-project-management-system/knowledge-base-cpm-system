from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid


class LoginSchema(BaseModel):
    login: str
    password: str


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenCreateSchema(BaseModel):
    jti: str
    user_id: uuid.UUID
    family_id: str
    expires_at: datetime
    replaced_by_jti: uuid.UUID | None = None


class StudentRegistrationSchema(BaseModel):
    first_name: str
    surname: str
    middle_name: str | None = None
    group: str
    student_number: str
    email: EmailStr
    password: str
    password_confirm: str
    role: str = "student"


class TeacherRegistrationSchema(BaseModel):
    first_name: str
    surname: str
    middle_name: str | None = None
    student_number: str | None = None
    email: EmailStr
    password: str
    password_confirm: str
    role: str = "teacher"


class RequestRefreshSchema(BaseModel):
    refresh_token: str
