from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import List


class ScheduleGenerateSchema(BaseModel):
    examiner: str
    year: int
    start_date: datetime
    end_date: datetime
    duration_minutes: int

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date <= self.end_date:
            raise ValueError("Start date must be grater than end date")

        return self


class ScheduleResponseSchema(BaseModel):
    schedule: List[datetime]
