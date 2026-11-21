from fastapi import FastAPI
from app.api.router import router as api_router
import uvicorn

app = FastAPI(title="API-Gateway")

app.include_router(api_router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True, host="127.0.0.1", port=8000)
