import logging
from app.database.models import Watchlist
from app.database.repositories import WatchlistRepository

logger = logging.getLogger(__name__)


class WatchlistService:
    def __init__(self, repository: WatchlistRepository):
        self.repository = repository

    def _normalize_symbol(self, symbol: str) -> str:
        return symbol.strip().upper()

    async def get_watchlist(self, user_id: int) -> list[Watchlist]:
        return await self.repository.get_by_user_id(user_id)

    async def add_to_watchlist(self, user_id: int, symbol: str, company_name: str | None = None) -> Watchlist:
        symbol = self._normalize_symbol(symbol)
        if not symbol:
            raise ValueError("Symbol cannot be empty")
        return await self.repository.add(user_id, symbol, company_name)

    async def remove_from_watchlist(self, user_id: int, symbol: str) -> bool:
        symbol = self._normalize_symbol(symbol)
        if not symbol:
            return False
        return await self.repository.remove(user_id, symbol)

    async def clear_watchlist(self, user_id: int) -> int:
        return await self.repository.clear(user_id)
