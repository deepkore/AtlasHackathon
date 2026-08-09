import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NewsError(RuntimeError):
    pass


class NewsClient:
    def __init__(self, api_key: str, base_url: str = "https://newsapi.org/v2", timeout: float = 15.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search_financial_news(
        self,
        query: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise NewsError("News API key is not configured")
        to_date = to_date or datetime.now(UTC).date().isoformat()
        from_date = from_date or (datetime.now(UTC).date() - timedelta(days=7)).isoformat()
        data = await self._get(
            "/everything",
            {
                "q": query,
                "from": from_date,
                "to": to_date,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 5,
            },
        )
        return {
            "query": query,
            "articles": [
                {
                    "headline": item.get("title"),
                    "summary": item.get("description"),
                    "source": (item.get("source") or {}).get("name"),
                    "url": item.get("url"),
                    "published_at": item.get("publishedAt"),
                }
                for item in data.get("articles", [])[:5]
            ],
        }

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = {"X-Api-Key": self.api_key}
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, headers=headers) as client:
                response = await client.get(path, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            logger.warning("News request timed out")
            raise NewsError("News request timed out") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("News request failed with status %s", exc.response.status_code)
            raise NewsError("News request failed") from exc
        except httpx.HTTPError as exc:
            logger.warning("News HTTP error")
            raise NewsError("News request failed") from exc
