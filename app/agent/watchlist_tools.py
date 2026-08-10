from typing import Any
from app.agent.tools import ToolDefinition
from app.services.watchlist import WatchlistService


def build_watchlist_tools(watchlist_service: WatchlistService) -> list[ToolDefinition]:
    async def get_watchlist(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        items = await watchlist_service.get_watchlist(user_id)
        if not items:
            return {"message": "Your watchlist is empty."}
        return {"watchlist": [{"symbol": item.symbol, "company_name": item.company_name} for item in items]}

    async def add_to_watchlist(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        symbol = arguments.get("symbol")
        company_name = arguments.get("company_name")
        if not symbol:
            return {"error": True, "message": "Symbol is required."}
        await watchlist_service.add_to_watchlist(user_id, symbol, company_name)
        return {"message": f"Added {symbol} to watchlist."}

    async def remove_from_watchlist(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        symbol = arguments.get("symbol")
        if not symbol:
            return {"error": True, "message": "Symbol is required."}
        removed = await watchlist_service.remove_from_watchlist(user_id, symbol)
        if not removed:
            return {"message": f"{symbol} was not in the watchlist."}
        return {"message": f"Removed {symbol} from watchlist."}

    async def clear_watchlist(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        count = await watchlist_service.clear_watchlist(user_id)
        return {"message": f"Cleared {count} items from watchlist."}

    return [
        ToolDefinition(
            "get_watchlist",
            "Retrieve the companies/symbols the user is currently tracking.",
            {"type": "object", "properties": {}},
            get_watchlist
        ),
        ToolDefinition(
            "add_to_watchlist",
            "Add a company stock symbol to the user's watchlist.",
            {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The stock ticker symbol (e.g. NVDA)"},
                    "company_name": {"type": "string", "description": "Optional name of the company"}
                },
                "required": ["symbol"]
            },
            add_to_watchlist
        ),
        ToolDefinition(
            "remove_from_watchlist",
            "Remove a company stock symbol from the user's watchlist.",
            {
                "type": "object",
                "properties": {"symbol": {"type": "string", "description": "The stock ticker symbol (e.g. NVDA)"}},
                "required": ["symbol"]
            },
            remove_from_watchlist
        ),
        ToolDefinition(
            "clear_watchlist",
            "Remove all symbols from the user's watchlist.",
            {"type": "object", "properties": {}},
            clear_watchlist
        )
    ]
