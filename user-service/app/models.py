from sqlalchemy import (
    DateTime,
    func,
    String,
    Integer,
    Boolean,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from enum import StrEnum
from datetime import datetime
import uuid


class UserRole(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class User(Base):
    __tablename__ = "users"

    email = mapped_column(String(255), unique=True, nullable=True, index=True)
    student_number = mapped_column(String(32), unique=True, nullable=True, index=True)
    password_hash = mapped_column(String, nullable=False)
    role = mapped_column(String, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "(role = 'teacher' AND email IS NOT NULL AND student_number IS NULL) OR "
            "(role = 'admin'   AND email IS NOT NULL AND student_number IS NULL) OR "
            "(role = 'student' AND student_number IS NOT NULL)",
            name="ck_users_login_identifier",
        ),
        CheckConstraint(
            "student_number IS NULL OR student_number ~ '^[0-9]{8}$'",
            name="ck_users_student_number_format",
        ),
        CheckConstraint(
            "email IS NULL OR email ~* '^[^@[:space:]]+@[^@[:space:]]+$'",
            name="ck_users_email_format",
        ),
    )

    student_profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    teacher_profile: Mapped["TeacherProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id : Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    first_name = mapped_column(String(100), nullable=False)
    last_name = mapped_column(String(100), nullable=False)
    middle_name = mapped_column(String(100), nullable=False)
    group = mapped_column(String(16), nullable=False)
    technologies: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        nullable=False,
        server_default="{}",
    )

    user: Mapped["User"] = relationship(back_populates="student_profile")


class TeacherProfile(Base):
    __tablename__ = "teacher_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    first_name = mapped_column(String(100), nullable=False)
    surname = mapped_column(String(100), nullable=False)
    middle_name = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship(back_populates="teacher_profile")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    jti = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    family_id = mapped_column(String, index=True, nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    revoked = mapped_column(Boolean, default=False, nullable=False)
    replaced_by_jti = mapped_column(String, nullable=True)
