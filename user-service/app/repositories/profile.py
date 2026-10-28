import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import StudentProfile, TeacherProfile


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_student_profile(
        self, user_id: uuid.UUID
    ) -> StudentProfile | None:
        return await self.session.scalar(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )

    async def get_teacher_profile(
        self, user_id: uuid.UUID
    ) -> TeacherProfile | None:
        return await self.session.scalar(
            select(TeacherProfile).where(TeacherProfile.user_id == user_id)
        )

    async def create_student_profile(
        self,
        user_id: uuid.UUID,
        **fields,
    ) -> StudentProfile:
        profile = StudentProfile(user_id=user_id, **fields)
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def create_teacher_profile(
        self,
        user_id: uuid.UUID,
        **fields,
    ) -> TeacherProfile:
        profile = TeacherProfile(user_id=user_id, **fields)
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def update_student_profile(
        self, user_id: uuid.UUID, **fields
    ) -> StudentProfile | None:
        profile = await self.get_student_profile(user_id)
        if profile is None:
            return None
        for name, value in fields.items():
            setattr(profile, name, value)
        await self.session.flush()
        return profile

    async def update_teacher_profile(
        self, user_id: uuid.UUID, **fields
    ) -> TeacherProfile | None:
        profile = await self.get_teacher_profile(user_id)
        if profile is None:
            return None
        for name, value in fields.items():
            setattr(profile, name, value)
        await self.session.flush()
        return profile