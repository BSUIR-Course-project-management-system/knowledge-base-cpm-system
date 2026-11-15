from fastapi import APIRouter, BackgroundTasks

from app.api.deps import StorageDep
from app.schemas import RefreshResponse

router = APIRouter(prefix="/cache", tags=["cache"])


@router.post("/refresh", response_model=RefreshResponse, status_code=202)
def refresh(background_tasks: BackgroundTasks, storage: StorageDep):
    storage.try_start_refresh()  # бросает RefreshInProgressError
    background_tasks.add_task(storage.run_refresh)
    return storage.refresh_status()  # status="started"


@router.get("/status", response_model=RefreshResponse)
def status(storage: StorageDep):
    return storage.refresh_status()
