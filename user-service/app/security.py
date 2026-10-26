from fastapi import HTTPException, status
import datetime
import uuid
from typing import Tuple, Dict
import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from .config import settings

oauth2_schema = OAuth2PasswordBearer(tokenUrl="/login")
password_hash = PasswordHash.recommended()

UTC = datetime.timezone.utc


def _now() -> datetime.datetime:
    return datetime.datetime.now(UTC)


def generate_access_token(user_id: uuid.UUID, role: str) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "role": role,
        "exp": now + datetime.timedelta(minutes=int(settings.ACCESS_TTL)),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def generate_refresh_token(
    user_id: uuid.UUID, family_id: str
) -> Tuple[str, str, datetime.datetime]:
    now = _now()
    jti = str(uuid.uuid4())
    expires_at = now + datetime.timedelta(days=int(settings.REFRESH_TTl))

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "family_id": family_id,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_refresh_token(token: str) -> Dict:
    try:
        payload = jwt.decode(
            token, key=settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired."
        )
    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)
