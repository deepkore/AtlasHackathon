from app.schemas.telegram import TelegramUpdate


def test_telegram_update_parsing():
    update = TelegramUpdate.model_validate(
        {
            "update_id": 1,
            "message": {
                "message_id": 10,
                "from": {"id": 42, "is_bot": False, "first_name": "Deep", "username": "deep"},
                "chat": {"id": 99, "type": "private"},
                "text": "Tell me about Nvidia.",
            },
        }
    )

    assert update.sender().id == 42
    assert update.chat_id() == 99
    assert update.inbound_text() == "Tell me about Nvidia."

