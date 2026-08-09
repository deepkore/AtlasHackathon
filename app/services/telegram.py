import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TelegramError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, bot_token: str, timeout: float = 10.0):
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        self.bot_token = bot_token
        self.timeout = timeout
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(self, chat_id: int, text: str) -> dict[str, Any]:
        return await self._post("sendMessage", {"chat_id": chat_id, "text": text})

    async def get_webhook_info(self) -> dict[str, Any]:
        return await self._post("getWebhookInfo", {})

    async def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                response = await client.post(f"/{method}", json=payload)
                response.raise_for_status()
                data = response.json()
                if not data.get("ok", False):
                    raise TelegramError(f"Telegram method {method} returned ok=false")
                return data
        except httpx.TimeoutException as exc:
            logger.warning("Telegram request timed out for method %s", method)
            raise TelegramError("Telegram request timed out") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("Telegram request failed with status %s for method %s", exc.response.status_code, method)
            raise TelegramError("Telegram request failed") from exc
        except httpx.HTTPError as exc:
            logger.warning("Telegram HTTP error for method %s", method)
            raise TelegramError("Telegram request failed") from exc
