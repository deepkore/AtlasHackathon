import respx
import httpx
import pytest
from httpx import Response

from app.finance.finnhub import FinnhubClient, FinnhubError


@respx.mock
async def test_finnhub_stock_quote_success():
    route = respx.get("https://finnhub.io/api/v1/quote").mock(
        return_value=Response(
            200,
            json={"c": 100.0, "d": 1.5, "dp": 1.52, "h": 101.0, "l": 98.0, "o": 99.0, "pc": 98.5, "t": 1710000000},
        )
    )

    response = await FinnhubClient(api_key="fake").get_stock_quote("NVDA")

    assert route.called
    assert response["current_price"] == 100.0
    assert response["timestamp"] == "2024-03-09T16:00:00+00:00"


async def test_finnhub_missing_api_key():
    with pytest.raises(FinnhubError):
        await FinnhubClient(api_key="").get_stock_quote("NVDA")


@respx.mock
async def test_finnhub_timeout():
    respx.get("https://finnhub.io/api/v1/quote").mock(side_effect=httpx.TimeoutException("slow"))

    with pytest.raises(FinnhubError):
        await FinnhubClient(api_key="fake").get_stock_quote("NVDA")


@respx.mock
async def test_finnhub_api_error():
    respx.get("https://finnhub.io/api/v1/quote").mock(return_value=Response(500, json={"error": "bad"}))

    with pytest.raises(FinnhubError):
        await FinnhubClient(api_key="fake").get_stock_quote("NVDA")


@respx.mock
async def test_finnhub_company_profile():
    respx.get("https://finnhub.io/api/v1/stock/profile2").mock(
        return_value=Response(
            200,
            json={
                "name": "NVIDIA Corporation",
                "exchange": "NASDAQ",
                "finnhubIndustry": "Semiconductors",
                "country": "US",
                "marketCapitalization": 3000,
                "weburl": "https://nvidia.com",
            },
        )
    )

    response = await FinnhubClient(api_key="fake").get_company_profile("NVDA")

    assert response["name"] == "NVIDIA Corporation"
    assert response["industry"] == "Semiconductors"


@respx.mock
async def test_finnhub_company_news():
    respx.get("https://finnhub.io/api/v1/company-news").mock(
        return_value=Response(
            200,
            json=[
                {
                    "headline": "Nvidia rises",
                    "summary": "Shares moved higher.",
                    "source": "Example",
                    "url": "https://example.com/nvda",
                    "datetime": 1710000000,
                }
            ],
        )
    )

    response = await FinnhubClient(api_key="fake").get_company_news("NVDA", "2024-03-01", "2024-03-09")

    assert response["articles"][0]["headline"] == "Nvidia rises"


@respx.mock
async def test_finnhub_earnings():
    respx.get("https://finnhub.io/api/v1/stock/earnings").mock(
        return_value=Response(200, json=[{"period": "2024-Q1", "actual": 1.2, "estimate": 1.1, "surprise": 0.1}])
    )

    response = await FinnhubClient(api_key="fake").get_company_earnings("AAPL")

    assert response["earnings"][0]["period"] == "2024-Q1"
