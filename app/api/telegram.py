import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import Agent
from app.config import Settings, get_settings
from app.database.repositories import UserRepository
from app.database.session import get_db_session
from app.dependencies import agent_dependency, get_telegram_client
from app.schemas.telegram import TelegramUpdate
from app.services.telegram import TelegramClient, TelegramError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["telegram"])

FALLBACK_RESPONSE = "Atlas is having trouble responding right now. Please try again shortly."


@router.post("/telegram")
async def telegram_webhook(
    update: TelegramUpdate,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db_session),
    agent: Agent = Depends(agent_dependency),
    telegram_client: TelegramClient = Depends(get_telegram_client),
) -> dict[str, bool]:
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram webhook secret")

    text = update.inbound_text()
    sender = update.sender()
    chat_id = update.chat_id()
    if not text or sender is None or chat_id is None:
        logger.info("Ignoring Telegram update without supported text message")
        return {"ok": True}

    try:
        user = await UserRepository(session).get_or_create_from_telegram(sender)
        response_text = await agent.respond(user_id=user.id, message=text)
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Failed to process Telegram update")
        response_text = FALLBACK_RESPONSE

    try:
        logger.info("Sending Telegram response to chat_id=%s length=%s", chat_id, len(response_text))
        await telegram_client.send_message(chat_id=chat_id, text=response_text)
    except TelegramError:
        logger.exception("Failed to send Telegram response")

    return {"ok": True}
