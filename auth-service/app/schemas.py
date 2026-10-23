from pydantic import BaseModel, EmailStr


class LoginSchema(BaseModel):
    login: str
    password: str


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str


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
