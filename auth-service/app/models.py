from sqlalchemy import DateTime, func, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
import uuid


class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class User(Base):
    __tablename__ = "users"
    pass


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    jti = mapped_column(String, unique=True, index=True, nullable=False)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    family_id = mapped_column(String, index=True, nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked = mapped_column(Boolean, default=False, nullable=False)
    replaced_by_jti = mapped_column(String, nullable=True)
