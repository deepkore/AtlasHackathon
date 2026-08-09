import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class FinnhubError(RuntimeError):
    pass


class FinnhubClient:
    def __init__(self, api_key: str, base_url: str = "https://finnhub.io/api/v1", timeout: float = 15.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        if not self.api_key:
            raise FinnhubError("Finnhub API key is not configured")
        data = await self._get("/quote", {"symbol": symbol.upper()})
        timestamp = data.get("t")
        return {
            "symbol": symbol.upper(),
            "current_price": data.get("c"),
            "change": data.get("d"),
            "change_percent": data.get("dp"),
            "high": data.get("h"),
            "low": data.get("l"),
            "open": data.get("o"),
            "previous_close": data.get("pc"),
            "timestamp": datetime.fromtimestamp(timestamp, tz=UTC).isoformat() if timestamp else None,
        }

    async def get_company_profile(self, symbol: str) -> dict[str, Any]:
        if not self.api_key:
            raise FinnhubError("Finnhub API key is not configured")
        data = await self._get("/stock/profile2", {"symbol": symbol.upper()})
        return {
            "symbol": symbol.upper(),
            "name": data.get("name"),
            "exchange": data.get("exchange"),
            "industry": data.get("finnhubIndustry"),
            "country": data.get("country"),
            "market_cap": data.get("marketCapitalization"),
            "website": data.get("weburl"),
        }

    async def get_company_news(self, symbol: str, from_date: str | None = None, to_date: str | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise FinnhubError("Finnhub API key is not configured")
        to_date = to_date or datetime.now(UTC).date().isoformat()
        from_date = from_date or (datetime.now(UTC).date() - timedelta(days=7)).isoformat()
        data = await self._get("/company-news", {"symbol": symbol.upper(), "from": from_date, "to": to_date})
        articles = [
            {
                "headline": item.get("headline"),
                "summary": item.get("summary"),
                "source": item.get("source"),
                "url": item.get("url"),
                "published_at": datetime.fromtimestamp(item["datetime"], tz=UTC).isoformat()
                if item.get("datetime")
                else None,
            }
            for item in (data or [])[:5]
        ]
        return {"symbol": symbol.upper(), "articles": articles}

    async def get_company_earnings(self, symbol: str) -> dict[str, Any]:
        if not self.api_key:
            raise FinnhubError("Finnhub API key is not configured")
        data = await self._get("/stock/earnings", {"symbol": symbol.upper()})
        return {
            "symbol": symbol.upper(),
            "earnings": [
                {
                    "period": item.get("period"),
                    "actual": item.get("actual"),
                    "estimate": item.get("estimate"),
                    "surprise": item.get("surprise"),
                    "surprise_percent": item.get("surprisePercent"),
                }
                for item in (data or [])[:8]
            ],
        }

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        params = {**params, "token": self.api_key}
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                response = await client.get(path, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            logger.warning("Finnhub request timed out for path %s", path)
            raise FinnhubError("Finnhub request timed out") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("Finnhub request failed with status %s for path %s", exc.response.status_code, path)
            raise FinnhubError("Finnhub request failed") from exc
        except httpx.HTTPError as exc:
            logger.warning("Finnhub HTTP error for path %s", path)
            raise FinnhubError("Finnhub request failed") from exc
