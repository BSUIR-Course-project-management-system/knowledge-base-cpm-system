from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SortBy = Literal["grade", "year", "title", "is_used"]
Year = Annotated[int, Field(ge=1990, le=3000)]
Name = Annotated[str, Field(min_length=1)]


class Base(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class TopicRequest(Base):
    year: Year | None = None
    is_used: bool | None = None
    curator: str | None = None
    examiner: str | None = None
    sort_by: SortBy | None = None


class MilestoneScheduleRequest(Base):
    year: Year
    examiner: str | None = None


class RefreshResponse(Base):
    status: Literal["started", "running", "ok", "failed"]
    record_count: int = 0
    updated_at: datetime | None = None


class TopicOut(Base):
    id: str
    year: Year
    topic: Name
    description: str | None = None
    is_used: bool = False
    curator: str | None = None
    examiner: str | None = None
    date_defence: str | None = None
    rounded_final_grade: int | None = None
    technologies: str|None = None


class TopicsPage(Base):
    total: int = Field(ge=0)
    items: list[TopicOut]


class MilestoneOut(Base):
    id: str
    examiner: Name
    topic_title: Name
    start: datetime
    end: datetime
    hold_format: str
    note: str | None = None


class MilestoneScheduleOut(Base):
    year: Year
    milestones: dict[str, list[MilestoneOut]] = {
        "milestone_1": [],
        "milestone_2": [],
        "milestone_3": [],
    }


class StudentOut(Base):
    number: int
    name: Name
    topic_title: str | None = None
    topic_comment: str | None = None
    is_topic_accepted: bool = False
    curator: str | None = None
    examiner: str | None = None
    curator_note: str | None = None
    curator_penalty_point: int | None = None


class GroupOut(Base):
    group_id: str
    students: list[StudentOut] = []
