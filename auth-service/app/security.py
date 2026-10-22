from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from typing import Dict
from .config import settings
import datetime
import jwt

oauth2_schema = OAuth2PasswordBearer(tokenUrl="/login")

password_hash = PasswordHash.recommended()


def encode_token(payload: Dict) -> str:
    to_encode = payload.copy()
    expires_at = datetime.datetime.now() + datetime.timedelta(
        minutes=int(settings.expired_minutes)
    )
    to_encode.update({"exp": expires_at})
    return jwt.encode(
        payload=to_encode, key=settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)
