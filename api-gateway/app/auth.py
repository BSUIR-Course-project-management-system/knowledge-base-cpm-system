import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.config import settings
from typing import Dict

bearer = HTTPBearer()


def decode_access_token(token: str) -> Dict:
    try:
        payload = jwt.decode(
            token, key=settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    return payload
