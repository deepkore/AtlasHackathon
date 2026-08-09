from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Message, User
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

