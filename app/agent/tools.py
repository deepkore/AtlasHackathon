import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.finance.finnhub import FinnhubClient, FinnhubError
from app.finance.news import NewsClient, NewsError
from app.finance.sec import SECClient, SECError
from app.services.preferences import PreferenceService
from app.services.watchlist import WatchlistService

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any], int], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler

    def declaration(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.input_schema}

    async def run(self, arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        return await self.handler(arguments, user_id)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def all(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def declarations(self) -> list[dict[str, Any]]:
        return [tool.declaration() for tool in self.all()]

    async def execute(self, name: str, arguments: dict[str, Any], request_id: str, user_id: int) -> dict[str, Any]:
        tool = self.get(name)
        if tool is None:
            return {"error": True, "message": "The requested tool is unavailable."}
        started = time.perf_counter()
        try:
            result = await tool.run(arguments, user_id)
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "agent_tool_executed",
                extra={
                    "user_id": user_id,
                    "agent_request_id": request_id,
                    "tool_name": name,
                    "duration_ms": duration_ms,
                    "success": not result.get("error"),
                },
            )
            return result
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "agent_tool_failed",
                extra={
                    "user_id": user_id,
                    "agent_request_id": request_id,
                    "tool_name": name,
                    "duration_ms": duration_ms,
                    "success": False,
                },
            )
            return {"error": True, "message": "The data service is temporarily unavailable."}


def symbol_schema(description: str = "Public equity ticker symbol, e.g. NVDA") -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"symbol": {"type": "string", "description": description}},
        "required": ["symbol"],
    }


def _string_arg(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    return str(value).strip() if value is not None else ""


def _missing(message: str) -> dict[str, Any]:
    return {"error": True, "message": message}


def build_tool_registry(finnhub_client: FinnhubClient, sec_client: SECClient, news_client: NewsClient) -> ToolRegistry:
    registry = ToolRegistry()

    async def get_stock_quote(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        symbol = _string_arg(arguments, "symbol").upper()
        if not symbol:
            return _missing("A stock symbol is required.")
        try:
            return {"source": "Finnhub", **await finnhub_client.get_stock_quote(symbol)}
        except FinnhubError:
            return {"error": True, "message": "The stock data service is temporarily unavailable."}

    async def get_company_profile(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        symbol = _string_arg(arguments, "symbol").upper()
        if not symbol:
            return _missing("A stock symbol is required.")
        try:
            return {"source": "Finnhub", **await finnhub_client.get_company_profile(symbol)}
        except FinnhubError:
            return {"error": True, "message": "The company profile service is temporarily unavailable."}

    async def get_company_news(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        symbol = _string_arg(arguments, "symbol").upper()
        if not symbol:
            return _missing("A stock symbol is required.")
        try:
            return {
                "source": "Finnhub",
                **await finnhub_client.get_company_news(
                    symbol=symbol,
                    from_date=_string_arg(arguments, "from_date") or None,
                    to_date=_string_arg(arguments, "to_date") or None,
                ),
            }
        except FinnhubError:
            return {"error": True, "message": "The company news service is temporarily unavailable."}

    async def get_company_earnings(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        symbol = _string_arg(arguments, "symbol").upper()
        if not symbol:
            return _missing("A stock symbol is required.")
        try:
            return {"source": "Finnhub", **await finnhub_client.get_company_earnings(symbol)}
        except FinnhubError:
            return {"error": True, "message": "The earnings service is temporarily unavailable."}

    async def get_company_filings(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        symbol = _string_arg(arguments, "symbol") or _string_arg(arguments, "ticker")
        if not symbol:
            return _missing("A ticker symbol is required.")
        try:
            return {"source": "SEC EDGAR", **await sec_client.get_company_filings(symbol)}
        except SECError:
            return {"error": True, "message": "SEC filing data is temporarily unavailable."}

    async def get_latest_sec_filing(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        symbol = _string_arg(arguments, "symbol")
        form = _string_arg(arguments, "form").upper()
        if not symbol or not form:
            return _missing("A stock symbol and SEC form are required.")
        try:
            return {"source": "SEC EDGAR", **await sec_client.get_latest_sec_filing(symbol, form)}
        except SECError:
            return {"error": True, "message": "SEC filing data is temporarily unavailable."}

    async def get_company_facts(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        symbol = _string_arg(arguments, "symbol")
        if not symbol:
            return _missing("A stock symbol is required.")
        try:
            return {"source": "SEC EDGAR", **await sec_client.get_company_facts(symbol)}
        except SECError:
            return {"error": True, "message": "SEC company facts are temporarily unavailable."}

    async def search_financial_news(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        query = _string_arg(arguments, "query")
        if not query:
            return _missing("A news search query is required.")
        try:
            return {
                "source": "NewsAPI",
                **await news_client.search_financial_news(
                    query=query,
                    from_date=_string_arg(arguments, "from_date") or None,
                    to_date=_string_arg(arguments, "to_date") or None,
                ),
            }
        except NewsError:
            return {"error": True, "message": "The news search service is temporarily unavailable."}

    date_props = {
        "from_date": {"type": "string", "description": "Optional ISO date, YYYY-MM-DD"},
        "to_date": {"type": "string", "description": "Optional ISO date, YYYY-MM-DD"},
    }

    registry.register(ToolDefinition("get_stock_quote", "Retrieve the latest available stock quote.", symbol_schema(), get_stock_quote))
    registry.register(ToolDefinition("get_company_profile", "Retrieve normalized company profile information.", symbol_schema(), get_company_profile))
    registry.register(
        ToolDefinition(
            "get_company_news",
            "Retrieve a small recent set of company news articles.",
            {
                "type": "object",
                "properties": {**symbol_schema()["properties"], **date_props},
                "required": ["symbol"],
            },
            get_company_news,
        )
    )
    registry.register(ToolDefinition("get_company_earnings", "Retrieve recent company earnings results.", symbol_schema(), get_company_earnings))
    registry.register(ToolDefinition("get_company_filings", "Retrieve recent SEC filings for a company.", symbol_schema("Ticker symbol, e.g. MSFT"), get_company_filings))
    registry.register(
        ToolDefinition(
            "get_latest_sec_filing",
            "Retrieve the latest SEC filing matching a form type.",
            {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Ticker symbol, e.g. MSFT"},
                    "form": {"type": "string", "description": "SEC form type, e.g. 10-K, 10-Q, 8-K"},
                },
                "required": ["symbol", "form"],
            },
            get_latest_sec_filing,
        )
    )
    registry.register(ToolDefinition("get_company_facts", "Retrieve normalized SEC XBRL company facts.", symbol_schema("Ticker symbol, e.g. MSFT"), get_company_facts))
    registry.register(
        ToolDefinition(
            "search_financial_news",
            "Search recent financial news for a query.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Financial news search query"},
                    **date_props,
                },
                "required": ["query"],
            },
            search_financial_news,
        )
    )
    return registry


def build_tools(
    finnhub_client: FinnhubClient, 
    sec_client: SECClient, 
    news_client: NewsClient,
    preference_service: PreferenceService,
    watchlist_service: WatchlistService,
    task_repo: Any = None,
) -> list[ToolDefinition]:
    from app.agent.preference_tools import build_preference_tools
    from app.agent.watchlist_tools import build_watchlist_tools
    from app.agent.scheduling_tools import build_scheduling_tools

    registry = build_tool_registry(finnhub_client, sec_client, news_client)
    tools = registry.all()
    tools.extend(build_preference_tools(preference_service))
    tools.extend(build_watchlist_tools(watchlist_service))
    
    if task_repo is not None:
        tools.extend(build_scheduling_tools(task_repo))
        
    return tools
