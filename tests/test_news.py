import respx
from httpx import Response

from app.finance.news import NewsClient, NewsError


@respx.mock
async def test_news_search():
    route = respx.get("https://newsapi.org/v2/everything").mock(
        return_value=Response(
            200,
            json={
                "articles": [
                    {
                        "title": "Nvidia expands AI platform",
                        "description": "A short summary.",
                        "source": {"name": "Example News"},
                        "url": "https://example.com/story",
                        "publishedAt": "2024-03-09T12:00:00Z",
                    }
                ]
            },
        )
    )

    response = await NewsClient(api_key="fake").search_financial_news("Nvidia AI")

    assert route.called
    assert response["articles"][0]["source"] == "Example News"


async def test_news_missing_api_key():
    try:
        await NewsClient(api_key="").search_financial_news("Nvidia")
    except NewsError as exc:
        assert "key" in str(exc)
    else:
        raise AssertionError("expected NewsError")
