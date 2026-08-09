from app.database.models import Message
from app.database.repositories import MessageRepository
from app.schemas.agent import ConversationMessage


class ConversationService:
    def __init__(self, message_repository: MessageRepository, context_limit: int = 12):
        self.message_repository = message_repository
        self.context_limit = context_limit

    async def add_user_message(self, user_id: int, content: str) -> Message:
        return await self.message_repository.add(user_id=user_id, role="user", content=content)

    async def add_assistant_message(self, user_id: int, content: str) -> Message:
        return await self.message_repository.add(user_id=user_id, role="assistant", content=content)

    async def get_context(self, user_id: int) -> list[ConversationMessage]:
        messages = await self.message_repository.latest_for_user(user_id=user_id, limit=self.context_limit)
        return [ConversationMessage(role=message.role, content=message.content) for message in messages]

