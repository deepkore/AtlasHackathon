from app.api.telegram import FALLBACK_RESPONSE
from app.dependencies import agent_dependency, get_telegram_client
from app.main import app


class FakeAgent:
    async def respond(self, user_id: int, message: str) -> str:
        assert message == "Hello Atlas"
        return "Hello from Atlas"


class FakeTelegramClient:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id: int, text: str):
        self.messages.append((chat_id, text))
        return {"ok": True}


async def test_telegram_webhook_flow(client):
    fake_telegram = FakeTelegramClient()

    async def override_agent():
        yield FakeAgent()

    def override_telegram_client():
        return fake_telegram

    app.dependency_overrides[agent_dependency] = override_agent
    app.dependency_overrides[get_telegram_client] = override_telegram_client

    response = await client.post(
        "/webhooks/telegram",
        headers={"x-telegram-bot-api-secret-token": ""},
        json={
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 123, "first_name": "Deep"},
                "chat": {"id": 456, "type": "private"},
                "text": "Hello Atlas",
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fake_telegram.messages == [(456, "Hello from Atlas")]

