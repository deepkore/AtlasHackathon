import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.telegram import router as telegram_router
from app.config import get_settings
from app.services.scheduler import Scheduler

logging.basicConfig(level=logging.INFO)

scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    settings = get_settings()
    if settings.scheduler_enabled:
        scheduler = Scheduler(poll_interval=settings.scheduler_poll_interval_seconds)
        scheduler.start()
    yield
    if scheduler:
        scheduler.stop()

app = FastAPI(title="Atlas Financial Assistant API", lifespan=lifespan)

@app.get("/health")
async def health() -> dict[str, str | bool]:
    global scheduler
    return {
        "status": "ok",
        "scheduler_running": scheduler._running if scheduler else False
    }


app.include_router(telegram_router)

