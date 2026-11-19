from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from app.auth import decode_access_token, bearer
from app.schemas import CurrentUserOutSchema
import uuid


def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(bearer),
) -> CurrentUserOutSchema:
    payload = decode_access_token(token.credentials)
    return CurrentUserOutSchema(
        user_id=uuid.UUID(payload["sub"]), role=payload["role"], sid=payload["sid"]
    )


def require_roles(*roles):
    async def checker(user=Depends(get_current_user)) -> CurrentUserOutSchema:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You dont have permissions for this action",
            )

        return user

    return checker
