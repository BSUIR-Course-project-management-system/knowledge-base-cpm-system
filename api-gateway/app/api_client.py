import httpx
from fastapi import HTTPException, status, Header
from typing import Any, Dict


def _upstream_error(response: httpx.Response) -> HTTPException:
    try:
        detail = response.json()
    except ValueError:
        detail = response.text or response.reason_phrase

    return HTTPException(status_code=response.status_code, detail=detail)


async def request_service(
    method: str,
    url: str,
    body: Any | None = None,
    headers: Dict[str, Any] | None = None,
    params: Dict[str, Any] | None = None,
):

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method, url=url, json=body, headers=headers, params=params
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{e.request.url}",
            )

    if response.status_code >= 400:
        raise _upstream_error(response)

    return response.json()
