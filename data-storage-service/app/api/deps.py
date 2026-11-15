from typing import Annotated

from fastapi import Depends, Request

from app.storage_module.storage import StorageInterface


def get_storage(request: Request) -> StorageInterface:
    return request.app.state.storage


StorageDep = Annotated[StorageInterface, Depends(get_storage)]
