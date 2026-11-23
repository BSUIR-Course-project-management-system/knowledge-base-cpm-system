from fastapi.requests import Request
from typing import Dict


def get_proxy_headers(request: Request) -> dict[str, str]:
    exclude_headers = {
        "host",
        "content-length",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "upgrade",
        "proxy-connection",
        "proxy-authorization",
        "te",
        "trailer",
    }

    return {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in exclude_headers
    }
