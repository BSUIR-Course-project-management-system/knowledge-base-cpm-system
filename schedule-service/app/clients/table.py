from fastapi import HTTPException, status
import httpx
from typing import Dict, Any
from app.config import settings


class TableClient:
    async def get_milestones(self, examiner: str, year: int) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                milestones = await client.get(
                    f"{settings.DATA_STORAGE_URL}/milestones?{examiner=}&{year=}"
                )

            return milestones.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{exc.request.url}",
            )
