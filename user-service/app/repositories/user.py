from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.security import hash_password
from typing import Sequence
import uuid


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> User | None:
        smth = select(User).where(User.id == id)
        user = await self.session.scalar(smth)
        return user

    async def list(self, limit: int = 10, offset: int = 0) -> Sequence[User]:
        smth = select(User).limit(limit).offset(offset)
        users = (await self.session.execute(smth)).scalars().all()
        return users

    async def create(self, **kwargs):
        user = User(**kwargs)
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, id: uuid.UUID, **kwargs) -> User:
        user = await self.get_by_id(id)

        for field, value in kwargs.items():
            if value is None:
                continue

            if field == "password_hash":
                value = hash_password(field)

            setattr(user, field, value)

        await self.session.flush()
        return user  # type: ignore

    async def delete(self, id: uuid.UUID) -> None:
        smth = delete(User).where(User.id == id)
        await self.session.execute(smth)
