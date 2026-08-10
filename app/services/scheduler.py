import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.database.session import get_db_session
from app.database.repositories import ScheduledTaskRepository, NotificationHistoryRepository
from app.services.briefing import BriefingService
from app.config import get_settings
from app.dependencies import get_llm_provider, get_telegram_client
from app.finance.finnhub import FinnhubClient
from app.finance.news import NewsClient
from app.finance.sec import SECClient
from app.services.preferences import PreferenceService
from app.services.watchlist import WatchlistService
from app.database.repositories import UserPreferenceRepository, WatchlistRepository

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, poll_interval: int = 30):
        self.poll_interval = poll_interval
        self._running = False
        self._task = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info(f"Scheduler started with {self.poll_interval}s interval.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Scheduler stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self._process_due_tasks()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(self.poll_interval)

    async def _process_due_tasks(self):
        async for session in get_db_session():
            task_repo = ScheduledTaskRepository(session)
            # Find tasks where next_run_at <= now
            due_tasks = await task_repo.get_due_tasks()
            
            if not due_tasks:
                return

            logger.info(f"Scheduler found {len(due_tasks)} due tasks.")
            settings = get_settings()
            
            # Setup dependencies for BriefingService
            llm = get_llm_provider(settings)
            telegram = get_telegram_client(settings)
            pref_repo = UserPreferenceRepository(session)
            watch_repo = WatchlistRepository(session)
            notif_repo = NotificationHistoryRepository(session)
            
            pref_service = PreferenceService(pref_repo)
            watch_service = WatchlistService(watch_repo)
            
            finnhub = FinnhubClient(api_key=settings.finnhub_api_key, timeout=settings.http_timeout_seconds)
            sec = SECClient(timeout=settings.http_timeout_seconds, user_agent=f"{settings.sec_user_agent} {settings.sec_contact_email}".strip())
            news = NewsClient(api_key=settings.news_api_key, timeout=settings.http_timeout_seconds)
            
            briefing_service = BriefingService(
                llm, telegram, pref_service, watch_service, notif_repo, finnhub, sec, news, settings
            )
            
            now_utc = datetime.now(timezone.utc)
            
            for task in due_tasks:
                try:
                    await briefing_service.run_briefing(task)
                except Exception as e:
                    logger.error(f"Task {task.id} failed: {e}")
                finally:
                    # Update task next_run_at and last_run_at
                    task.last_run_at = now_utc
                    task.next_run_at = self._calculate_next_run(task, now_utc)
                    await task_repo.update(task)
            
            await session.commit()
            break # only one session needed

    def _calculate_next_run(self, task, now_utc: datetime) -> datetime:
        # Simple schedule calculation logic.
        # Expects task.schedule to have {"time": "HH:MM", "frequency": "daily" | "weekdays"}
        tz_name = task.timezone or "UTC"
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = timezone.utc
            
        now_local = now_utc.astimezone(tz)
        
        time_str = task.schedule.get("time", "08:00")
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            hour, minute = 8, 0
            
        # Target time today
        target = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if target <= now_local:
            # Move to tomorrow
            from datetime import timedelta
            target += timedelta(days=1)
            
        frequency = task.schedule.get("frequency", "daily")
        if frequency == "weekdays":
            while target.weekday() >= 5: # 5=Sat, 6=Sun
                target += timedelta(days=1)
                
        return target.astimezone(timezone.utc)
