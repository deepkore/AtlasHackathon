import respx
from httpx import Response

from app.finance.sec import SECClient, SECError


TICKERS = {"0": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"}}


@respx.mock
async def test_sec_filings():
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(return_value=Response(200, json=TICKERS))
    respx.get("https://data.sec.gov/submissions/CIK0000789019.json").mock(
        return_value=Response(
            200,
            json={
                "name": "MICROSOFT CORP",
                "filings": {
                    "recent": {
                        "form": ["10-K", "4"],
                        "filingDate": ["2024-07-30", "2024-07-31"],
                        "reportDate": ["2024-06-30", "2024-07-30"],
                        "accessionNumber": ["0000950170-24-087843", "x"],
                        "primaryDocument": ["msft-20240630.htm", "x.htm"],
                    }
                },
            },
        )
    )

    response = await SECClient(user_agent="Atlas tests test@example.com").get_company_filings("MSFT")

    assert response["company"] == "MICROSOFT CORP"
    assert response["filings"][0]["form"] == "10-K"
    assert "Archives/edgar/data/789019" in response["filings"][0]["url"]


@respx.mock
async def test_sec_latest_filing():
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(return_value=Response(200, json=TICKERS))
    respx.get("https://data.sec.gov/submissions/CIK0000789019.json").mock(
        return_value=Response(
            200,
            json={
                "name": "MICROSOFT CORP",
                "filings": {
                    "recent": {
                        "form": ["8-K", "10-K"],
                        "filingDate": ["2024-08-01", "2024-07-30"],
                        "reportDate": ["2024-08-01", "2024-06-30"],
                        "accessionNumber": ["a", "b"],
                        "primaryDocument": ["a.htm", "b.htm"],
                    }
                },
            },
        )
    )

    response = await SECClient(user_agent="Atlas tests test@example.com").get_latest_sec_filing("MSFT", "10-K")

    assert response["filing"]["form"] == "10-K"


@respx.mock
async def test_sec_company_facts():
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(return_value=Response(200, json=TICKERS))
    respx.get("https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json").mock(
        return_value=Response(
            200,
            json={
                "entityName": "MICROSOFT CORP",
                "facts": {
                    "us-gaap": {
                        "Revenues": {
                            "units": {
                                "USD": [
                                    {"val": 100, "fy": 2023, "fp": "FY", "end": "2023-06-30", "form": "10-K", "filed": "2023-07-30"},
                                    {"val": 120, "fy": 2024, "fp": "FY", "end": "2024-06-30", "form": "10-K", "filed": "2024-07-30"},
                                ]
                            }
                        }
                    }
                },
            },
        )
    )

    response = await SECClient(user_agent="Atlas tests test@example.com").get_company_facts("MSFT")

    assert response["metrics"]["revenue"]["value"] == 120
    assert response["metrics"]["net_income"] is None


@respx.mock
async def test_sec_api_error():
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(return_value=Response(500))

    try:
        await SECClient(user_agent="Atlas tests test@example.com").get_company_filings("MSFT")
    except SECError as exc:
        assert "SEC request failed" in str(exc)
    else:
        raise AssertionError("expected SECError")
