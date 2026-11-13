from fastapi import FastAPI, Depends
from app.service import Service
from app.schemas import ScheduleResponseSchema, ScheduleGenerateSchema
from app.dependencies import get_service
import uvicorn

app = FastAPI()


@app.post("/milestone-schedule", response_model=ScheduleResponseSchema)
async def generate_schedule(
    schema: ScheduleGenerateSchema, service: Service = Depends(get_service)
):
    return await service.generate_schedule(schema)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8002, reload=True)
