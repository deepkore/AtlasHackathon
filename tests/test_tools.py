from app.agent.tools import ToolDefinition, ToolRegistry, build_tool_registry


class FakeFinnhub:
    async def get_stock_quote(self, symbol):
        return {"symbol": symbol, "current_price": 100}

    async def get_company_profile(self, symbol):
        return {"symbol": symbol, "name": "NVIDIA Corporation"}

    async def get_company_news(self, symbol, from_date=None, to_date=None):
        return {"symbol": symbol, "articles": [{"headline": "News"}]}

    async def get_company_earnings(self, symbol):
        return {"symbol": symbol, "earnings": [{"period": "2024-Q1"}]}


class FakeSEC:
    async def get_company_filings(self, symbol):
        return {"symbol": symbol, "filings": []}

    async def get_latest_sec_filing(self, symbol, form):
        return {"symbol": symbol, "form": form, "filing": {"form": form}}

    async def get_company_facts(self, symbol):
        return {"symbol": symbol, "metrics": {"revenue": {"value": 1}}}


class FakeNews:
    async def search_financial_news(self, query, from_date=None, to_date=None):
        return {"query": query, "articles": [{"headline": "Market story"}]}


async def test_tool_registry():
    async def handler(arguments, user_id):
        return {"ok": arguments["ok"]}

    registry = ToolRegistry()
    registry.register(ToolDefinition("example", "Example", {"type": "object"}, handler))

    assert registry.get("example").name == "example"
    assert registry.declarations()[0]["parameters"] == {"type": "object"}
    assert await registry.execute("example", {"ok": True}, request_id="r1", user_id=1) == {"ok": True}


async def test_tool_registry_unknown_tool():
    result = await ToolRegistry().execute("missing", {}, request_id="r1", user_id=1)

    assert result["error"] is True


async def test_built_tools_execute_all_success_paths():
    registry = build_tool_registry(FakeFinnhub(), FakeSEC(), FakeNews())

    assert len(registry.declarations()) == 8
    assert (await registry.execute("get_stock_quote", {"symbol": "nvda"}, "r1", 1))["current_price"] == 100
    assert (await registry.execute("get_company_profile", {"symbol": "nvda"}, "r1", 1))["name"] == "NVIDIA Corporation"
    assert (await registry.execute("get_company_news", {"symbol": "nvda"}, "r1", 1))["articles"][0]["headline"] == "News"
    assert (await registry.execute("get_company_earnings", {"symbol": "aapl"}, "r1", 1))["earnings"][0]["period"] == "2024-Q1"
    assert (await registry.execute("get_company_filings", {"symbol": "msft"}, "r1", 1))["source"] == "SEC EDGAR"
    assert (await registry.execute("get_latest_sec_filing", {"symbol": "msft", "form": "10-K"}, "r1", 1))["filing"]["form"] == "10-K"
    assert (await registry.execute("get_company_facts", {"symbol": "msft"}, "r1", 1))["metrics"]["revenue"]["value"] == 1
    assert (await registry.execute("search_financial_news", {"query": "Nvidia"}, "r1", 1))["articles"][0]["headline"] == "Market story"


async def test_built_tool_missing_symbol():
    registry = build_tool_registry(FakeFinnhub(), FakeSEC(), FakeNews())

    result = await registry.execute("get_stock_quote", {}, "r1", 1)

    assert result["error"] is True
    assert "symbol" in result["message"].lower()
