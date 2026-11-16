from fastapi import APIRouter, HTTPException

from app.api.deps import StorageDep
from app.schemas import GroupOut

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupOut])
def list_groups(storage: StorageDep):
    return storage.list_groups()


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: str, storage: StorageDep):
    group = storage.get_group(group_id)
    if group is None:
        raise HTTPException(404, f"Группа {group_id} не найдена")
    return group
