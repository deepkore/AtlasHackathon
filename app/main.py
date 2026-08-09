import logging

from fastapi import FastAPI

from app.api.telegram import router as telegram_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Atlas Financial Assistant API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(telegram_router)

