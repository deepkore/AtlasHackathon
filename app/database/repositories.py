from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.database.models import Message, NotificationHistory, ScheduledTask, User, UserPreference, Watchlist
from app.schemas.telegram import TelegramUser


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_from_telegram(self, telegram_user: TelegramUser) -> User:
        result = await self.session.execute(select(User).where(User.telegram_user_id == telegram_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_user_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
            )
            self.session.add(user)
            await self.session.flush()
            return user

        user.username = telegram_user.username
        user.first_name = telegram_user.first_name
        user.last_name = telegram_user.last_name
        await self.session.flush()
        return user


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: int, role: str, content: str) -> Message:
        message = Message(user_id=user_id, role=role, content=content)
        self.session.add(message)
        await self.session.flush()
        return message

    async def latest_for_user(self, user_id: int, limit: int) -> list[Message]:
        stmt = select(Message).where(Message.user_id == user_id).order_by(Message.created_at.desc(), Message.id.desc()).limit(limit)
        result = await self.session.execute(stmt)
        messages = list(result.scalars())
        return list(reversed(messages))


class UserPreferenceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: int) -> UserPreference | None:
        result = await self.session.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(self, user_id: int, role: str | None = None, interests: list[str] | None = None) -> UserPreference:
        pref = UserPreference(user_id=user_id, role=role, interests=interests or [])
        self.session.add(pref)
        await self.session.flush()
        return pref

    async def update(self, user_id: int, **kwargs) -> UserPreference | None:
        pref = await self.get_by_user_id(user_id)
        if not pref:
            return None
        for key, value in kwargs.items():
            if hasattr(pref, key):
                setattr(pref, key, value)
        await self.session.flush()
        return pref

    async def upsert(self, user_id: int, **kwargs) -> UserPreference:
        pref = await self.get_by_user_id(user_id)
        if pref:
            return await self.update(user_id, **kwargs)
        return await self.create(user_id, **kwargs)

    async def delete(self, user_id: int) -> bool:
        pref = await self.get_by_user_id(user_id)
        if not pref:
            return False
        await self.session.delete(pref)
        await self.session.flush()
        return True


class WatchlistRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: int) -> list[Watchlist]:
        stmt = select(Watchlist).where(Watchlist.user_id == user_id).order_by(Watchlist.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def get_by_symbol(self, user_id: int, symbol: str) -> Watchlist | None:
        stmt = select(Watchlist).where(Watchlist.user_id == user_id, Watchlist.symbol == symbol)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, user_id: int, symbol: str) -> bool:
        return await self.get_by_symbol(user_id, symbol) is not None

    async def add(self, user_id: int, symbol: str, company_name: str | None = None) -> Watchlist:
        existing = await self.get_by_symbol(user_id, symbol)
        if existing:
            return existing
        item = Watchlist(user_id=user_id, symbol=symbol, company_name=company_name)
        self.session.add(item)
        await self.session.flush()
        return item

    async def remove(self, user_id: int, symbol: str) -> bool:
        item = await self.get_by_symbol(user_id, symbol)
        if not item:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True

    async def clear(self, user_id: int) -> int:
        items = await self.get_by_user_id(user_id)
        count = len(items)
        for item in items:
            await self.session.delete(item)
        await self.session.flush()
        return count


class ScheduledTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: int) -> list[ScheduledTask]:
        stmt = select(ScheduledTask).where(ScheduledTask.user_id == user_id).order_by(ScheduledTask.next_run_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars())
        
    async def get_by_id(self, task_id: int, user_id: int) -> ScheduledTask | None:
        stmt = select(ScheduledTask).where(ScheduledTask.id == task_id, ScheduledTask.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_due_tasks(self, limit: int = 50) -> list[ScheduledTask]:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        stmt = (
            select(ScheduledTask)
            .where(
                ScheduledTask.enabled == True,
                ScheduledTask.next_run_at <= now
            )
            .order_by(ScheduledTask.next_run_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def create(self, user_id: int, task_type: str, schedule: dict, timezone: str | None = None) -> ScheduledTask:
        task = ScheduledTask(
            user_id=user_id,
            task_type=task_type,
            schedule=schedule,
            timezone=timezone
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def update(self, task: ScheduledTask) -> ScheduledTask:
        self.session.add(task)
        await self.session.flush()
        return task

    async def delete(self, task: ScheduledTask) -> None:
        await self.session.delete(task)
        await self.session.flush()


class NotificationHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def has_been_notified(self, user_id: int, event_key: str) -> bool:
        stmt = select(NotificationHistory).where(
            NotificationHistory.user_id == user_id, 
            NotificationHistory.event_key == event_key
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add(self, user_id: int, event_key: str, notification_type: str, title: str, summary: str, source_url: str | None = None) -> NotificationHistory:
        notification = NotificationHistory(
            user_id=user_id,
            event_key=event_key,
            notification_type=notification_type,
            title=title,
            summary=summary,
            source_url=source_url
        )
        self.session.add(notification)
        # Handle potential duplicates via ignore if needed, but doing simple add for now
        await self.session.flush()
        return notification
