"""Dynamic Yahoo universe via custom screener (production discovery).

Implements the existing ``InstrumentSource`` protocol. Returns the exact
Yahoo symbols returned by the screener, filtered by the approved universe
contract (EQUITY, WSE, pl_market, PLN, 0.10 <= price <= 10.00). No symbol is
constructed, suffixed, or repaired via Search/Lookup.

Instantaneous accepted-record snapshot (safe fields only) and neutral
discovery diagnostics are exposed and cleared at the start of each new
discovery. A screener error never triggers a static fallback and never keeps a
stale snapshot.
"""

from typing import List

from data.yahoo.yahoo_session import FetchResult, OutcomeKind, ScreenerPagination

SNAPSHOT_FIELDS = (
    "symbol",
    "quoteType",
    "exchange",
    "market",
    "currency",
    "regularMarketPrice",
)


class UniverseContract:
    """Approved acceptance rules for the dynamic WSE universe."""

    MIN_PRICE = 0.10
    MAX_PRICE = 10.00

    @staticmethod
    def accepts(quote: dict) -> bool:
        if quote.get("quoteType") != "EQUITY":
            return False
        if quote.get("exchange") != "WSE":
            return False
        if quote.get("market") != "pl_market":
            return False
        if quote.get("currency") != "PLN":
            return False

        price = quote.get("regularMarketPrice")
        if not isinstance(price, (int, float)) or isinstance(price, bool):
            return False
        return UniverseContract.MIN_PRICE <= price <= UniverseContract.MAX_PRICE


def _safe_snapshot(quote: dict) -> dict:
    return {field: quote.get(field) for field in SNAPSHOT_FIELDS}


class YahooDiscoverySource:
    """
    Dynamic instrument source backed by the Yahoo custom screener pagination.

    A neutral screener error yields an empty universe and never triggers an
    automatic fallback. Diagnostics are stored in ``last_discovery`` and the
    accepted snapshot in ``accepted_snapshot``.
    """

    def __init__(self, session):
        self._session = session
        self.accepted_snapshot: dict = {}
        self.last_discovery: dict = {}

    def get_instruments(self) -> List[str]:
        # Always clear the snapshot at the start of a new discovery so a stale
        # snapshot can never be used after a later screener error.
        self.accepted_snapshot = {}

        result: FetchResult = self._session.paginate_screener(size=250)

        self.last_discovery = {
            "outcome_kind": result.kind.value if hasattr(result.kind, "value") else str(result.kind),
            "total_records": 0,
            "accepted_count": 0,
            "rejected_count": 0,
            "error": result.message if result.message else None,
        }

        if result.kind != OutcomeKind.SUCCESS_WITH_DATA:
            return []

        pagination: ScreenerPagination = result.data
        symbols: List[str] = []
        seen = set()

        total_records = 0
        accepted_count = 0
        rejected_count = 0

        for page in pagination.pages:
            for quote in page.quotes:
                total_records += 1
                if not UniverseContract.accepts(quote):
                    rejected_count += 1
                    continue
                symbol = quote.get("symbol")
                if not isinstance(symbol, str) or symbol == "":
                    rejected_count += 1
                    continue
                if symbol in seen:
                    continue
                seen.add(symbol)
                accepted_count += 1
                symbols.append(symbol)
                self.accepted_snapshot[symbol] = _safe_snapshot(quote)

        self.last_discovery = {
            "outcome_kind": result.kind.value,
            "total_records": total_records,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "error": None,
        }

        return symbols