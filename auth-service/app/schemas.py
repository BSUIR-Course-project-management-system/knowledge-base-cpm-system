from pydantic import BaseModel, EmailStr


class LoginSchema(BaseModel):
    username: str
    password: str


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str


# TODO: Вход по студенческому
class StudentRegistrationSchema(BaseModel):
    first_name: str
    surname: str
    middle_name: str | None = None
    group: str
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
