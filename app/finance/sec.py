import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SECError(RuntimeError):
    pass


class SECClient:
    PRIORITY_FORMS = {"10-K", "10-Q", "8-K", "20-F", "6-K"}
    METRIC_TAGS = {
        "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
        "net_income": ["NetIncomeLoss"],
        "assets": ["Assets"],
        "liabilities": ["Liabilities"],
        "stockholders_equity": ["StockholdersEquity"],
        "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue", "CashAndCashEquivalents"],
    }

    def __init__(
        self,
        base_url: str = "https://data.sec.gov",
        sec_url: str = "https://www.sec.gov",
        timeout: float = 15.0,
        user_agent: str = "Atlas Financial Assistant contact@example.com",
    ):
        self.base_url = base_url.rstrip("/")
        self.sec_url = sec_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent

    async def get_company_filings(self, symbol: str, limit: int = 10) -> dict[str, Any]:
        ticker = symbol.upper()
        cik = await self.get_cik_for_ticker(ticker)
        submissions = await self._get_data(f"/submissions/CIK{cik.zfill(10)}.json")
        recent = submissions.get("filings", {}).get("recent", {})
        filings: list[dict[str, Any]] = []
        for index, form in enumerate(recent.get("form", [])):
            if form not in self.PRIORITY_FORMS:
                continue
            accession = recent.get("accessionNumber", [])[index]
            primary_document = recent.get("primaryDocument", [None])[index]
            cik_no_zeros = str(int(cik))
            accession_path = accession.replace("-", "")
            filings.append(
                {
                    "form": form,
                    "filing_date": recent.get("filingDate", [None])[index],
                    "report_date": recent.get("reportDate", [None])[index],
                    "accession_number": accession,
                    "primary_document": primary_document,
                    "url": f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_path}/{primary_document}"
                    if primary_document
                    else None,
                }
            )
            if len(filings) >= limit:
                break
        return {"symbol": ticker, "company": submissions.get("name"), "cik": cik, "filings": filings}

    async def get_latest_sec_filing(self, symbol: str, form: str) -> dict[str, Any]:
        filings = await self.get_company_filings(symbol=symbol, limit=40)
        normalized_form = form.upper()
        latest = next((filing for filing in filings["filings"] if filing["form"] == normalized_form), None)
        return {"symbol": symbol.upper(), "form": normalized_form, "filing": latest}

    async def get_company_facts(self, symbol: str) -> dict[str, Any]:
        ticker = symbol.upper()
        cik = await self.get_cik_for_ticker(ticker)
        facts = await self._get_data(f"/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json")
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        metrics = {
            metric_name: self._latest_metric(us_gaap, tags)
            for metric_name, tags in self.METRIC_TAGS.items()
        }
        return {"symbol": ticker, "company": facts.get("entityName"), "cik": cik, "metrics": metrics}

    async def get_cik_for_ticker(self, ticker: str) -> str:
        mapping = await self._get_sec("/files/company_tickers.json")
        for entry in mapping.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                return str(entry["cik_str"])
        raise SECError(f"SEC CIK not found for ticker {ticker.upper()}")

    async def _get_data(self, path: str) -> dict[str, Any]:
        return await self._get(self.base_url, path)

    async def _get_sec(self, path: str) -> dict[str, Any]:
        return await self._get(self.sec_url, path)

    async def _get(self, base_url: str, path: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url=base_url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
            ) as client:
                response = await client.get(path)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            logger.warning("SEC request timed out")
            raise SECError("SEC request timed out") from exc
        except httpx.HTTPError as exc:
            logger.warning("SEC request failed")
            raise SECError("SEC request failed") from exc

    @staticmethod
    def _latest_metric(us_gaap: dict[str, Any], tags: list[str]) -> dict[str, Any] | None:
        for tag in tags:
            item = us_gaap.get(tag)
            if not item:
                continue
            units = item.get("units", {})
            facts = units.get("USD") or next(iter(units.values()), [])
            useful = [fact for fact in facts if fact.get("val") is not None]
            if not useful:
                continue
            latest = sorted(useful, key=lambda fact: (fact.get("filed") or "", fact.get("end") or ""), reverse=True)[0]
            return {
                "tag": tag,
                "value": latest.get("val"),
                "unit": "USD" if "USD" in units else next(iter(units.keys()), None),
                "fy": latest.get("fy"),
                "fp": latest.get("fp"),
                "end": latest.get("end"),
                "form": latest.get("form"),
                "filed": latest.get("filed"),
            }
        return None
