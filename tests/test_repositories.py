from app.database.repositories import MessageRepository, UserRepository
from app.schemas.telegram import TelegramUser


async def test_user_creation(test_session):
    user = await UserRepository(test_session).get_or_create_from_telegram(
        TelegramUser(id=123, username="atlas_user", first_name="Atlas")
    )
    await test_session.commit()

    assert user.id is not None
    assert user.telegram_user_id == 123
    assert user.username == "atlas_user"


async def test_message_persistence(test_session):
    user = await UserRepository(test_session).get_or_create_from_telegram(TelegramUser(id=123))
    repo = MessageRepository(test_session)
    await repo.add(user_id=user.id, role="user", content="Hello")
    await repo.add(user_id=user.id, role="assistant", content="Hi")
    await test_session.commit()

    messages = await repo.latest_for_user(user_id=user.id, limit=10)

    assert [message.role for message in messages] == ["user", "assistant"]
    assert [message.content for message in messages] == ["Hello", "Hi"]

