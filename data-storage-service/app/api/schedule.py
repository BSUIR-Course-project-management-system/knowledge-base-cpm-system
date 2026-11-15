from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import StorageDep
from app.schemas import MilestoneScheduleOut, MilestoneScheduleRequest

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/milestones", response_model=MilestoneScheduleOut)
def get_milestones(
    params: Annotated[MilestoneScheduleRequest, Query()], storage: StorageDep
):
    return storage.get_milestones(params.year, params.examiner)
