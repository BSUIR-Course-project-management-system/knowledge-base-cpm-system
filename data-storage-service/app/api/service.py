from fastapi import APIRouter

router = APIRouter(tags=["service"])


@router.get("/health")
def health():
    return {"status": "ok"}
