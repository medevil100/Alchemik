"""
Yahoo Finance session: cookie/crumb bootstrap, custom screener with full
pagination, and chart (daily/intraday).

All network access goes through the injected ``Transport`` protocol, so offline
tests can substitute a fake. Secrets (A3 value, crumb value, Cookie headers)
are never logged, stored in result payloads, or exposed in metadata.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from http.cookiejar import Cookie

from .yahoo_transport import Transport
from urllib.parse import quote


FC_URL = "https://fc.yahoo.com/"
CRUMB_URL = "https://query1.finance.yahoo.com/v1/test/getcrumb"
SCREENER_URL = "https://query1.finance.yahoo.com/v1/finance/screener"
CHART_URL_TEMPLATE = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"


class YahooSessionError(Exception):
    """Raised for invalid bootstrap or pagination contract violations."""


class OutcomeKind(str, Enum):
    """Neutral transport-level outcome classification."""

    SUCCESS_WITH_DATA = "SUCCESS_WITH_DATA"
    SUCCESS_NO_DATA = "SUCCESS_NO_DATA"
    HTTP_ERROR = "HTTP_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    MISSING_FIELDS = "MISSING_FIELDS"
    TRANSPORT_EXCEPTION = "TRANSPORT_EXCEPTION"


@dataclass
class FetchResult:
    """Neutral result envelope returned by session operations."""

    kind: OutcomeKind
    data: object
    message: str | None


@dataclass
class ScreenerPage:
    total: int
    start: int
    count: int
    quotes: list


@dataclass
class ScreenerPagination:
    total: int
    pages: list


CHART_VARIANTS = {
    "daily": {"range": "1y", "interval": "1d"},
    "intraday": {"range": "5d", "interval": "5m"},
}


def _build_screener_body(offset: int, size: int) -> str:
    """Serialize the approved custom screener body."""
    body = {
        "offset": offset,
        "size": size,
        "sortField": "intradayprice",
        "sortType": "ASC",
        "userId": "",
        "userIdType": "guid",
        "quoteType": "EQUITY",
        "query": {
            "operator": "AND",
            "operands": [
                {"operator": "EQ", "operands": ["region", "pl"]},
                {"operator": "GTE", "operands": ["intradayprice", 0.10]},
                {"operator": "LTE", "operands": ["intradayprice", 10.00]},
            ],
        },
    }
    return json.dumps(body, separators=(",", ":"))


class YahooSession:
    """
    One fresh session for cookie, crumb, screener and chart.

    The crumb is kept only in memory and never persisted back into the cookie
    jar. Safe metadata (presence, domain, path, expiry-presence, crumb length
    and non-HTML flag) is the only secret-related output.
    """

    def __init__(self, transport: Transport):
        self._transport = transport
        self._crumb: str | None = None

    @property
    def request_count(self) -> int:
        """Liczba faktycznie wysłanych żądań transportu (diagnostyka Punktu 7)."""
        return int(getattr(self._transport, "request_count", 0))

    # ------------------------------------------------------------------
    # Cookie / crumb bootstrap
    # ------------------------------------------------------------------

    def _find_a3_cookie(self) -> Cookie | None:
        holder = getattr(self._transport, "cookies", None)
        jar = getattr(holder, "jar", None) if holder is not None else None
        if jar is None:
            return None
        for cookie in jar:
            if getattr(cookie, "name", None) == "A3":
                return cookie
        return None

    def _validate_a3(self, cookie: Cookie | None) -> dict:
        if cookie is None:
            raise YahooSessionError("A3 cookie missing from session jar")
        domain = getattr(cookie, "domain", None)
        if not isinstance(domain, str) or not (
            domain == "yahoo.com" or domain.endswith(".yahoo.com")
        ):
            raise YahooSessionError("A3 cookie domain is not a Yahoo domain")
        path = getattr(cookie, "path", None)
        if path != "/":
            raise YahooSessionError("A3 cookie path is not /")
        expires = getattr(cookie, "expires", None)
        if expires is None:
            raise YahooSessionError("A3 cookie has no expiry")
        return {
            "a3_present": True,
            "a3_domain": domain,
            "a3_path": path,
            "a3_expiry_present": True,
        }

    def bootstrap(self) -> dict:
        """
        Perform the cookie/crumb bootstrap.

        GET https://fc.yahoo.com/ may return HTTP 404; that is acceptable
        exactly when the fresh session received a valid A3 cookie.
        """
        cookie_response = self._transport.get(FC_URL, timeout=30)
        # Only HTTP 200 or HTTP 404 are acceptable. Any other status must abort
        # the bootstrap before the crumb request, even if an A3 is present.
        if cookie_response.status_code not in (200, 404):
            raise YahooSessionError(
                f"cookie bootstrap rejected HTTP {cookie_response.status_code}"
            )

        meta = self._validate_a3(self._find_a3_cookie())

        crumb_response = self._transport.get(CRUMB_URL, timeout=30)
        if crumb_response.status_code != 200:
            raise YahooSessionError(f"crumb endpoint returned HTTP {crumb_response.status_code}")

        crumb = crumb_response.text
        if crumb is None or crumb == "":
            raise YahooSessionError("crumb is empty")
        if "<html>" in crumb.lower():
            raise YahooSessionError("crumb looks like HTML")

        # Keep crumb only in memory; never write it back to the cookie jar.
        self._crumb = crumb

        meta["crumb_present"] = True
        meta["crumb_non_html"] = "<html>" not in crumb.lower()
        meta["crumb_length"] = len(crumb)
        return meta

    @property
    def crumb(self) -> str | None:
        return self._crumb

    def _ensure_bootstrapped(self) -> str:
        """Bootstrap once (cookie + crumb) if not already done."""
        if self._crumb is None:
            self.bootstrap()
        return self._crumb

    # ------------------------------------------------------------------
    # Custom screener
    # ------------------------------------------------------------------

    def _screener_params(self) -> dict:
        return {
            "crumb": self._crumb,
            "corsDomain": "finance.yahoo.com",
            "formatted": "false",
            "lang": "en-US",
            "region": "US",
        }

    def fetch_screener_page(self, offset: int = 0, size: int = 250) -> FetchResult:
        self._ensure_bootstrapped()
        data_body = _build_screener_body(offset, size)
        try:
            response = self._transport.post(
                SCREENER_URL,
                data=data_body,
                headers={"Content-Type": "application/json"},
                params=self._screener_params(),
                timeout=30,
            )
        except Exception as exc:  # noqa: BLE001 - transport boundary
            # Use the type name only: str(exc) could embed the request URL/params
            # and leak the crumb into logs/artifacts.
            return FetchResult(kind=OutcomeKind.TRANSPORT_EXCEPTION, data=None, message=type(exc).__name__)

        if response.status_code >= 400:
            return FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message=f"HTTP {response.status_code}")

        try:
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            return FetchResult(kind=OutcomeKind.PARSE_ERROR, data=None, message=str(exc))

        try:
            result = payload["finance"]["result"][0]
            page = ScreenerPage(
                total=result["total"],
                start=result["start"],
                count=result["count"],
                quotes=result.get("quotes", []),
            )
            return FetchResult(kind=OutcomeKind.SUCCESS_WITH_DATA, data=page, message=None)
        except (KeyError, IndexError, TypeError) as exc:
            return FetchResult(kind=OutcomeKind.MISSING_FIELDS, data=None, message=str(exc))

    def _validate_page(self, page: ScreenerPage, expected_start: int,
                       expected_total: int) -> None:
        if page.total != expected_total:
            raise YahooSessionError("screener total changed between pages")
        if page.start != expected_start:
            raise YahooSessionError(
                f"screener start mismatch: expected {expected_start}, got {page.start}"
            )
        if page.count != len(page.quotes):
            raise YahooSessionError("screener count does not match len(quotes)")
        if page.count == 0 and expected_total > 0:
            raise YahooSessionError("screener returned an empty page before total")

    def paginate_screener(self, size: int = 250) -> FetchResult:
        first = self.fetch_screener_page(offset=0, size=size)
        if first.kind != OutcomeKind.SUCCESS_WITH_DATA:
            return first

        first_page: ScreenerPage = first.data
        first_total = first_page.total
        self._validate_page(first_page, expected_start=0, expected_total=first_total)

        pages = [first_page]
        offset = size

        while offset < first_total:
            page_result = self.fetch_screener_page(offset=offset, size=size)
            if page_result.kind != OutcomeKind.SUCCESS_WITH_DATA:
                return page_result

            page: ScreenerPage = page_result.data
            self._validate_page(page, expected_start=offset, expected_total=first_total)

            pages.append(page)
            offset += size

        all_quotes = [q for p in pages for q in p.quotes]
        symbols = [q.get("symbol") for q in all_quotes if q.get("symbol")]
        if len(symbols) != len(set(symbols)):
            raise YahooSessionError("duplicate symbols across screener pages")
        if len(all_quotes) != first_total:
            raise YahooSessionError(
                f"screener record sum {len(all_quotes)} != total {first_total}"
            )

        return FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data=ScreenerPagination(total=first_total, pages=pages),
            message=None,
        )

    # ------------------------------------------------------------------
    # Chart
    # ------------------------------------------------------------------

    def fetch_chart(self, symbol: str, variant: str = "daily") -> FetchResult:
        """
        Fetch a chart for the exact Yahoo symbol.

        The symbol is URL-quoted (safe) but never otherwise modified.
        """
        if variant not in CHART_VARIANTS:
            return FetchResult(kind=OutcomeKind.MISSING_FIELDS, data=None, message=f"unknown variant {variant}")

        self._ensure_bootstrapped()
        url = CHART_URL_TEMPLATE.format(symbol=quote(symbol, safe=""))
        params = {
            **CHART_VARIANTS[variant],
            "includePrePost": "false",
            "events": "div,splits",
            "crumb": self._crumb,
        }

        captured_at = datetime.now(timezone.utc).isoformat()

        try:
            response = self._transport.get(url, params=params, timeout=30)
        except Exception as exc:  # noqa: BLE001
            # Use the type name only to avoid leaking URL/params (incl. crumb).
            return FetchResult(kind=OutcomeKind.TRANSPORT_EXCEPTION, data=None, message=type(exc).__name__)

        http_status = response.status_code
        if http_status >= 400:
            return FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message=f"HTTP {http_status}")

        try:
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            return FetchResult(kind=OutcomeKind.PARSE_ERROR, data=None, message=str(exc))

        chart = payload.get("chart") if isinstance(payload, dict) else None
        if not isinstance(chart, dict):
            return FetchResult(kind=OutcomeKind.MISSING_FIELDS, data=None, message="missing chart")

        result = chart.get("result")
        if result is None or (isinstance(result, list) and len(result) == 0):
            return FetchResult(kind=OutcomeKind.SUCCESS_NO_DATA, data=None, message=None)

        try:
            first = result[0]
            meta = first.get("meta", {})
            timestamp = first["timestamp"]
            quote_block = first["indicators"]["quote"][0]
            open_values = quote_block["open"]
            high = quote_block["high"]
            low = quote_block["low"]
            close = quote_block["close"]
            volume = quote_block["volume"]
            events = first.get("events", {})
        except (KeyError, IndexError, TypeError) as exc:
            return FetchResult(kind=OutcomeKind.MISSING_FIELDS, data=None, message=str(exc))

        normalized = {
            "variant": variant,
            "http_status": http_status,
            "captured_at": captured_at,
            "meta": meta,
            "timestamp": timestamp,
            "open": open_values,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "events": events,
        }
        return FetchResult(kind=OutcomeKind.SUCCESS_WITH_DATA, data=normalized, message=None)