import json

import respx
from httpx import Response

from app.services.telegram import TelegramClient


@respx.mock
async def test_telegram_client_mocked_response():
    route = respx.post("https://api.telegram.org/botfake/sendMessage").mock(return_value=Response(200, json={"ok": True}))

    response = await TelegramClient(bot_token="fake").send_message(chat_id=123, text="Hello")

    assert route.called
    assert response["ok"] is True


@respx.mock
async def test_telegram_client_sends_message_unchanged():
    route = respx.post("https://api.telegram.org/botfake/sendMessage").mock(return_value=Response(200, json={"ok": True}))

    text = "x" * 4500
    await TelegramClient(bot_token="fake").send_message(chat_id=123, text=text)

    sent_payload = json.loads(route.calls.last.request.content)
    assert sent_payload["text"] == text
