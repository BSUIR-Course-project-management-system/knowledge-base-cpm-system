import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import TokenRepository, UserRepository
from app.schemas import (
    LoginSchema,
    RequestRefreshSchema,
    StudentRegistrationSchema,
    TeacherRegistrationSchema,
    TokenCreateSchema,
    TokenResponseSchema,
)
from app.security import (
    decode_refresh_token,
    generate_access_token,
    generate_refresh_token,
    hash_password,
    verify_password,
)


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: TokenRepository,
        session: AsyncSession,
    ) -> None:
        self.session = session
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def register(
        self, data: StudentRegistrationSchema | TeacherRegistrationSchema
    ) -> TokenResponseSchema:
        if data.password != data.password_confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords must match.",
            )

        if await self.user_repo.email_exists(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists.",
            )

        student_number: str | None = None
        if isinstance(data, StudentRegistrationSchema):
            student_number = data.student_number
            if await self.user_repo.student_number_exists(student_number):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this student number already exists.",
                )

        user = await self.user_repo.create(
            email=data.email,
            student_number=student_number,
            password_hash=hash_password(data.password),
            role=data.role,
        )

        family_id = str(uuid.uuid4())
        access_token = generate_access_token(user.id, user.role)
        refresh_token, jti, expires_at = generate_refresh_token(user.id, family_id)

        await self.token_repo.create(
            TokenCreateSchema(
                jti=jti,
                user_id=user.id,
                family_id=family_id,
                expires_at=expires_at,
            )
        )

        await self.session.commit()

        return TokenResponseSchema(
            access_token=access_token, refresh_token=refresh_token
        )

    async def login(self, data: LoginSchema) -> TokenResponseSchema:
        user = await self.user_repo.get_by_login(data.login)

        if user is None or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )

        family_id = str(uuid.uuid4())
        access_token = generate_access_token(user.id, user.role)
        refresh_token, jti, expires_at = generate_refresh_token(user.id, family_id)

        await self.token_repo.create(
            TokenCreateSchema(
                jti=jti,
                user_id=user.id,
                family_id=family_id,
                expires_at=expires_at,
            )
        )

        await self.session.commit()

        return TokenResponseSchema(
            access_token=access_token, refresh_token=refresh_token
        )

    async def refresh(self, data: RequestRefreshSchema) -> TokenResponseSchema:
        payload = decode_refresh_token(data.refresh_token)
        jti = payload["jti"]

        refresh_token = await self.token_repo.get_by_jti(jti)
        if refresh_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown token."
            )

        if refresh_token.revoked:
            await self.token_repo.revoke_family(refresh_token.family_id)
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token reuse detection.",
            )

        user = await self.user_repo.get_by_id(uuid.UUID(payload["sub"]))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
            )

        new_refresh, new_jti, new_expires_at = generate_refresh_token(
            user.id,
            family_id=refresh_token.family_id,
        )
        new_access = generate_access_token(user.id, user.role)

        await self.token_repo.revoke(jti, new_jti)
        await self.token_repo.create(
            TokenCreateSchema(
                jti=new_jti,
                user_id=user.id,
                family_id=refresh_token.family_id,
                expires_at=new_expires_at,
            )
        )
        await self.session.commit()

        return TokenResponseSchema(access_token=new_access, refresh_token=new_refresh)

    async def list_users(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list:
        users = await self.user_repo.list(limit=limit, offset=offset)
        return list(users)

    async def get_user(self, user_id: uuid.UUID):
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return user

    async def update_user(self, user_id: uuid.UUID, **fields):
        current = await self.user_repo.get_by_id(user_id)
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        new_email = fields.get("email")
        if new_email is not None and new_email != current.email:
            existing = await self.user_repo.get_by_email(new_email)
            if existing is not None and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists.",
                )

        new_sn = fields.get("student_number")
        if new_sn is not None and new_sn != current.student_number:
            existing = await self.user_repo.get_by_student_number(new_sn)
            if existing is not None and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this student number already exists.",
                )

        user = await self.user_repo.update(user_id, **fields)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        await self.session.commit()
        return user

    async def delete_user(self, user_id: uuid.UUID) -> None:
        current = await self.user_repo.get_by_id(user_id)
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        await self.user_repo.delete(user_id)
        await self.session.commit()

    async def revoke_user_sessions(self, user_id: uuid.UUID) -> int:
        current = await self.user_repo.get_by_id(user_id)
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        count = await self.token_repo.revoke_all_for_user(user_id)
        await self.session.commit()
        return count
