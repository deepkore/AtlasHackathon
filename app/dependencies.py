from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import Agent
from app.agent.tools import build_tools
from app.config import Settings, get_settings
from app.database.repositories import MessageRepository
from app.database.session import get_db_session
from app.finance.finnhub import FinnhubClient
from app.finance.news import NewsClient
from app.finance.sec import SECClient
from app.llm.gemini import GeminiProvider
from app.services.conversation import ConversationService
from app.services.telegram import TelegramClient


def get_telegram_client(settings: Settings = Depends(get_settings)) -> TelegramClient:
    return TelegramClient(bot_token=settings.telegram_bot_token)


def get_llm_provider(settings: Settings) -> GeminiProvider:
    return GeminiProvider(api_key=settings.gemini_api_key, model=settings.llm_model)


async def get_agent(
    session: AsyncSession,
    settings: Settings,
) -> Agent:
    message_repository = MessageRepository(session)
    conversation_service = ConversationService(
        message_repository=message_repository,
        context_limit=settings.conversation_context_limit,
    )
    finnhub_client = FinnhubClient(api_key=settings.finnhub_api_key, timeout=settings.http_timeout_seconds)
    sec_client = SECClient(
        timeout=settings.http_timeout_seconds,
        user_agent=f"{settings.sec_user_agent} {settings.sec_contact_email}".strip(),
    )
    news_client = NewsClient(api_key=settings.news_api_key, timeout=settings.http_timeout_seconds)
    return Agent(
        llm_provider=get_llm_provider(settings),
        conversation_service=conversation_service,
        tools=build_tools(finnhub_client=finnhub_client, sec_client=sec_client, news_client=news_client),
        max_tool_calls=settings.max_tool_calls,
    )


async def agent_dependency(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[Agent, None]:
    yield await get_agent(session=session, settings=settings)
