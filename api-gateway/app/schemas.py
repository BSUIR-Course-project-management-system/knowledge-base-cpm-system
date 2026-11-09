from pydantic import BaseModel
import uuid


class CurrentUser(BaseModel):
    user_id: uuid.UUID
    role: str
