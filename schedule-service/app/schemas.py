from pydantic import BaseModel
from datetime import datetime
from typing import List


class ScheduleGenerateSchema(BaseModel):
    examiner: str
    year: int
    start_date: datetime
    end_date: datetime
    duration_minutes: int


class ScheduleResponseSchema(BaseModel):
    schedule: List[datetime]
