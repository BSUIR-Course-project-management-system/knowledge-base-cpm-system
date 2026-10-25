import uuid
from typing import Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import RefreshToken
from app.schemas import TokenCreateSchema


class TokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> RefreshToken | None:
        return await self.session.scalar(
            select(RefreshToken).where(RefreshToken.id == id)
        )

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        return await self.session.scalar(
            select(RefreshToken).where(RefreshToken.jti == jti)
        )

    async def get_by_family_id(self, family_id: str) -> Sequence[RefreshToken]:
        result = await self.session.execute(
            select(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .order_by(RefreshToken.created.desc())
        )
        return result.scalars().all()

    async def get_by_user_id(self, user_id: uuid.UUID) -> Sequence[RefreshToken]:
        result = await self.session.execute(
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .order_by(RefreshToken.created.desc())
        )
        return result.scalars().all()

    async def list(self, limit: int = 10, offset: int = 0) -> Sequence[RefreshToken]:
        result = await self.session.execute(
            select(RefreshToken)
            .order_by(RefreshToken.created.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def create(self, token: TokenCreateSchema) -> RefreshToken:
        db_token = RefreshToken(**token.model_dump())
        self.session.add(db_token)
        await self.session.flush()
        return db_token

    async def revoke(self, jti: str, replaced_by_jti: str | None = None) -> int:
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.jti == jti, RefreshToken.revoked.is_(False))
            .values(revoked=True, replaced_by_jti=replaced_by_jti)
        )
        return result.rowcount  # type: ignore

    async def revoke_family(self, family_id: str) -> int:
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        return result.rowcount  # type: ignore

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        return result.rowcount  # type: ignore
