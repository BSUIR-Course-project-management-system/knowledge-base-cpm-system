from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from datetime import datetime
import uuid
import re


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

    @field_validator("student_number", mode="after")
    @classmethod
    def valid_student_number(cls, value: str) -> str:
        if not re.fullmatch(r"^(?:[1-9][0-9]{7}|0[1-9][0-9]{6})$", value):
            raise ValueError(
                "Invalid student number. Must be 8 digits, optionally starting with a single zero."
            )
        return value

    @field_validator("group", mode="after")
    @classmethod
    def valid_group(cls, value: str) -> str:
        if not re.fullmatch(r"^(?:[1-9][0-9]{5}|0[1-9][0-9]{4})$", value):
            raise ValueError(
                "Invalid group. Must be 6 digits, optionally starting with a single zero."
            )
        return value


class TeacherRegistrationSchema(BaseModel):
    first_name: str
    surname: str
    middle_name: str | None = None
    email: EmailStr
    password: str
    password_confirm: str
    role: str = "teacher"


class RequestRefreshSchema(BaseModel):
    refresh_token: str


class UserOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr | None
    student_number: str | None
    role: str


class AdminUserUpdateSchema(BaseModel):
    email: EmailStr | None = None
    student_number: str | None = None
    role: str | None = None
