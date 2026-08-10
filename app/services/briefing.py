import logging
import asyncio
from datetime import datetime, timezone

from app.config import Settings
from app.database.models import ScheduledTask
from app.database.repositories import NotificationHistoryRepository
from app.finance.finnhub import FinnhubClient
from app.finance.news import NewsClient
from app.finance.sec import SECClient
from app.llm.base import LLMProvider
from app.schemas.agent import ConversationMessage
from app.schemas.briefing import BriefingDecision
from app.services.preferences import PreferenceService
from app.services.telegram import TelegramClient
from app.services.watchlist import WatchlistService

logger = logging.getLogger(__name__)


class BriefingService:
    def __init__(
        self,
        llm_provider: LLMProvider,
        telegram_client: TelegramClient,
        preference_service: PreferenceService,
        watchlist_service: WatchlistService,
        notification_repository: NotificationHistoryRepository,
        finnhub_client: FinnhubClient,
        sec_client: SECClient,
        news_client: NewsClient,
        settings: Settings,
    ):
        self.llm = llm_provider
        self.telegram = telegram_client
        self.preference_service = preference_service
        self.watchlist_service = watchlist_service
        self.notification_repo = notification_repository
        self.finnhub = finnhub_client
        self.sec = sec_client
        self.news = news_client
        self.settings = settings

    async def run_briefing(self, task: ScheduledTask) -> None:
        user_id = task.user_id
        logger.info(f"Running briefing for user {user_id}, task {task.id}")
        
        # Load user context
        pref = await self.preference_service.get_preferences(user_id)
        interests = pref.interests if pref else []
        watchlist = await self.watchlist_service.get_watchlist(user_id)
        symbols = [item.symbol for item in watchlist][:self.settings.max_watchlist_items_per_briefing]
        
        raw_data = await self._gather_financial_data(symbols, interests)
        filtered_data = await self._filter_duplicates(user_id, raw_data)
        
        if not filtered_data:
            logger.info("No new financial data to evaluate.")
            return

        decision = await self._evaluate_importance(filtered_data, interests, symbols)
        
        if decision.should_send and decision.importance_score >= self.settings.briefing_importance_threshold:
            if decision.items:
                await self._send_briefing(user_id, decision)
                await self._record_notifications(user_id, decision, filtered_data)
            else:
                logger.info("Decision was to send, but no items were provided.")
        else:
            logger.info(f"Information not important enough. Score: {decision.importance_score}")

    async def _gather_financial_data(self, symbols: list[str], interests: list[str]) -> list[dict]:
        data = []
        
        # Gather company news
        for symbol in symbols:
            try:
                news = await self.finnhub.get_company_news(symbol)
                for item in news.get("articles", [])[:3]:
                    data.append({
                        "type": "company_news",
                        "symbol": symbol,
                        "title": item.get("headline", ""),
                        "summary": item.get("summary", ""),
                        "url": item.get("url", ""),
                        "key": str(item.get("id", item.get("url", "")))
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch news for {symbol}: {e}")

        # Gather SEC filings
        for symbol in symbols:
            try:
                filings = await self.sec.get_company_filings(symbol)
                for item in filings.get("filings", [])[:2]:
                    data.append({
                        "type": "sec_filing",
                        "symbol": symbol,
                        "title": f"New {item.get('form')} Filing",
                        "summary": item.get("accession_number", ""),
                        "url": item.get("filing_url", ""),
                        "key": item.get("accession_number", "")
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch SEC filings for {symbol}: {e}")

        # Gather general interest news
        for interest in interests[:3]:
            try:
                news = await self.news.search_financial_news(interest)
                for item in news.get("articles", [])[:3]:
                    data.append({
                        "type": "interest_news",
                        "interest": interest,
                        "title": item.get("title", ""),
                        "summary": item.get("description", ""),
                        "url": item.get("url", ""),
                        "key": item.get("url", "")
                    })
            except Exception as e:
                logger.warning(f"Failed to search news for {interest}: {e}")

        return data

    async def _filter_duplicates(self, user_id: int, raw_data: list[dict]) -> list[dict]:
        filtered = []
        for item in raw_data:
            key = item.get("key")
            if not key:
                continue
            if not await self.notification_repo.has_been_notified(user_id, key):
                filtered.append(item)
        return filtered

    async def _evaluate_importance(self, data: list[dict], interests: list[str], symbols: list[str]) -> BriefingDecision:
        system_prompt = (
            "You are a financial analyst. Evaluate the following recent financial information for a user. "
            "Determine if there is anything genuinely meaningful and important that warrants a notification. "
            "Filter out routine or low-value information. Focus on significant movements, major announcements, "
            "earnings releases, or important SEC filings."
        )
        user_prompt = (
            f"User Interests: {', '.join(interests) if interests else 'None'}\n"
            f"User Watchlist: {', '.join(symbols) if symbols else 'None'}\n\n"
            "Recent Information:\n"
        )
        for i, item in enumerate(data):
            user_prompt += f"{i+1}. [{item.get('type')}] {item.get('title')}: {item.get('summary')} (URL: {item.get('url')})\n"
            
        messages = [
            ConversationMessage(role="system", content=system_prompt),
            ConversationMessage(role="user", content=user_prompt)
        ]
        
        return await self.llm.generate_structured(messages, BriefingDecision)

    async def _send_briefing(self, user_id: int, decision: BriefingDecision) -> None:
        lines = ["Good morning — here's what matters today:\n"] # TODO adapt greeting based on task type later if needed
        for item in decision.items:
            lines.append(f"📰 {item.title}")
            lines.append(f"{item.summary}")
            lines.append(f"Why it matters: {item.why_it_matters}")
            if item.source:
                url_part = f" ({item.source_url})" if item.source_url else ""
                lines.append(f"Source: {item.source}{url_part}")
            lines.append("")
            
        text = "\n".join(lines).strip()
        
        from app.database.session import get_db_session
        from sqlalchemy import select
        from app.database.models import User
        
        # Need telegram_user_id to send message
        async for session in get_db_session():
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                try:
                    await self.telegram.send_message(user.telegram_user_id, text)
                except Exception as e:
                    logger.error(f"Failed to send briefing to {user.telegram_user_id}: {e}")
            break

    async def _record_notifications(self, user_id: int, decision: BriefingDecision, original_data: list[dict]) -> None:
        for item in decision.items:
            # Match back to the original item to get the true event_key
            matched_item = None
            for data_item in original_data:
                data_url = data_item.get("url")
                data_title = data_item.get("title", "")
                if (item.source_url and item.source_url == data_url) or (item.title and item.title in data_title):
                    matched_item = data_item
                    break
                    
            event_key = matched_item.get("key") if matched_item else (item.source_url or item.title)
            
            try:
                await self.notification_repo.add(
                    user_id=user_id,
                    event_key=str(event_key)[:250],
                    notification_type="briefing",
                    title=item.title[:250],
                    summary=item.summary,
                    source_url=item.source_url
                )
            except Exception as e:
                logger.error(f"Failed to record notification history: {e}")
