from fastapi import Depends
from app.service import Service
from app.clients import TableClient


def get_table_client() -> TableClient:
    return TableClient()


def get_service(table_client: TableClient = Depends(get_table_client)) -> Service:
    return Service(table_client)
