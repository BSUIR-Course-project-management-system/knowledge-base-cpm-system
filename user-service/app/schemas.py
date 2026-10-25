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
    family_id: uuid.UUID
    expires_at: datetime
    replaced_by_jti: uuid.UUID


class StudentRegistrationSchema(BaseModel):
    first_name: str
    surname: str
    middle_name: str | None = None
    group: str
    student_number: str
    email: EmailStr
    password: str
    password_confirm: str


class TeacherRegistrationSchema(BaseModel):
    first_name: str
    surname: str
    middle_name: str | None = None
    group: str
    corporate_email: EmailStr
    password: str
    password_confirm: str
