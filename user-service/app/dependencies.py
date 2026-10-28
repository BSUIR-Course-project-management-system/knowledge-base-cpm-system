from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import UserRepository, TokenRepository, ProfileRepository
from app.db import async_session
from app.service import UserService
from typing import AsyncGenerator


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_user_repo(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return UserRepository(session)


def get_token_repo(session: AsyncSession = Depends(get_session)) -> TokenRepository:
    return TokenRepository(session)

def get_profile_repo(session: AsyncSession = Depends(get_session)) -> ProfileRepository:
    return ProfileRepository(session)


def get_service(
    session: AsyncSession = Depends(get_session),
    user_repo: UserRepository = Depends(get_user_repo),
    token_repo: TokenRepository = Depends(get_token_repo),
    profile_repo: ProfileRepository = Depends(get_profile_repo)
) -> UserService:
    return UserService(user_repo, token_repo, profile_repo, session)
