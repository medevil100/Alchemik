"""Yahoo chart-based ScanProvider adapter.

Implements the existing ``ScanProvider`` protocol (returning the actual
runtime shape ``List[Dict]`` with ``{"symbol", "data"}``). Normalizes chart
OHLCV arrays into the existing ``MarketData`` model with strict validation.

Rules enforced before a row/record may pass:
- the chart's ``meta.symbol`` must exactly equal the requested symbol;
- ``meta.instrumentType`` must be ``"EQUITY"``;
- ``meta.currency`` must be ``"PLN"``;
- ``meta.exchangeName`` must be ``"WSE"``;
- if a discovery snapshot is available, its symbol/quoteType/currency/exchange
  must be consistent with the chart such that a conflicting record is rejected;
- history must contain at least one complete, valid row;
- timestamp/open/high/low/close/volume arrays must have identical lengths;
- timestamps must be numeric, unique and strictly increasing;
- OHLCV must be numeric and finite;
- volume must not be negative (``volume=0`` is a valid value);
- per-row ``high >= open/low/close`` and ``low <= open/high/close``;
- missing values must never be invented or padded.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from data.models.market_data import MarketData
from data.yahoo.yahoo_session import FetchResult, OutcomeKind


class YahooChartProvider:
    """Fetches daily chart history for each discovered symbol.

    Diagnostics for the last scan are exposed via ``last_scan`` (a list of
    dicts) and are cleared at the start of every ``scan()`` call. The public
    result shape of ``scan()`` is unchanged.
    """

    def __init__(self, session, discovery_source=None):
        self._session = session
        self._discovery_source = discovery_source
        self.last_scan: List[dict] = []
        self.last_matrix: List[dict] = []

    # ------------------------------------------------------------------
    # Public contract
    # ------------------------------------------------------------------

    def scan(self, instruments: List[str]) -> List[Dict[str, Union[str, List[MarketData]]]]:
        self.last_scan = []
        results = []
        for symbol in instruments:
            result = self._session.fetch_chart(symbol, variant="daily")
            accepted, market_data, diag = self._validate(symbol, result)
            self.last_scan.append(diag)
            if accepted and market_data:
                results.append({"symbol": symbol, "data": market_data})
        return results

    def fetch_intraday(self, instruments: List[str]) -> Dict[str, dict]:
        """Krok 4/8 — addytywnie pobiera intraday (5d/5m) per symbol.

        Nie zmienia publicznego kontraktu ``scan()`` (daily pozostaje w
        ``scanner.scan()`` — dokładnie jeden daily per symbol w cyklu).
        Zwraca per symbol: {"accepted", "market_data", "diag"}.
        Zawsze zawiera wpis per symbol — brak/ błąd jest jawną diagnostyką.
        """
        self.last_matrix = []
        result_map: Dict[str, dict] = {}
        for symbol in instruments:
            result = self._session.fetch_chart(symbol, variant="intraday")
            accepted, market_data, diag = self._validate(symbol, result)
            result_map[symbol] = {
                "accepted": bool(accepted),
                "market_data": market_data or [],
                "diag": diag,
            }
            self.last_matrix.append({
                "symbol": symbol,
                "intraday_diag": diag,
            })
        return result_map

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self, symbol: str, result: FetchResult):
        base = {
            "symbol": symbol,
            "outcome_kind": result.kind.value if hasattr(result.kind, "value") else str(result.kind),
            "accepted": False,
            "reasons": [],
            "raw_rows": 0,
            "valid_rows": 0,
            "rejected_rows": 0,
            "rejection_reasons": {},
            "latest_raw_timestamp": None,
            "latest_valid_timestamp": None,
            "http_status": None,
            "error_kind": "none",
            "variant": None,
        }

        if result.kind != OutcomeKind.SUCCESS_WITH_DATA:
            base["reasons"].append("endpoint_not_success_with_data")
            base["error_kind"] = "fatal"
            return False, [], base

        data = result.data
        if not isinstance(data, dict):
            base["reasons"].append("no_chart_data")
            base["error_kind"] = "fatal"
            return False, [], base

        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        base["variant"] = data.get("variant")
        base["http_status"] = data.get("http_status")

        # Identity and metadata checks.
        # A missing optional field is not a conflict; an explicitly different
        # value is a conflict and must reject the record.
        if "symbol" in meta and meta.get("symbol") != symbol:
            base["reasons"].append("meta_symbol_mismatch")
        if "instrumentType" in meta and meta.get("instrumentType") != "EQUITY":
            base["reasons"].append("instrument_type_not_equity")
        if "currency" in meta and meta.get("currency") != "PLN":
            base["reasons"].append("currency_not_pln")
        if "exchangeName" in meta and meta.get("exchangeName") != "WSE":
            base["reasons"].append("exchange_name_not_wse")

        # Discovery snapshot consistency (optional, but reject on conflict).
        snapshot = None
        if self._discovery_source is not None:
            snapshot = getattr(self._discovery_source, "accepted_snapshot", {}).get(symbol)
        if snapshot is not None:
            if snapshot.get("symbol") != symbol:
                base["reasons"].append("discovery_symbol_mismatch")
            if snapshot.get("quoteType") != "EQUITY":
                base["reasons"].append("discovery_quote_type_not_equity")
            if snapshot.get("currency") != "PLN":
                base["reasons"].append("discovery_currency_not_pln")
            if snapshot.get("exchange") != "WSE":
                base["reasons"].append("discovery_exchange_not_wse")

        if base["reasons"]:
            base["error_kind"] = "fatal"
            return False, [], base

        # History checks.
        timestamps = data.get("timestamp")
        open_values = data.get("open")
        high_values = data.get("high")
        low_values = data.get("low")
        close_values = data.get("close")
        volume_values = data.get("volume")

        if not isinstance(timestamps, list) or len(timestamps) == 0:
            base["reasons"].append("empty_timestamps")
            base["error_kind"] = "fatal"
            return False, [], base

        arrays = [open_values, high_values, low_values, close_values, volume_values]
        if any(not isinstance(a, list) for a in arrays):
            base["reasons"].append("length_mismatch")
            base["error_kind"] = "fatal"
            return False, [], base

        n = len(timestamps)
        if any(len(a) != n for a in arrays):
            base["reasons"].append("length_mismatch")
            base["error_kind"] = "fatal"
            return False, [], base

        base["raw_rows"] = n

        # Timestamp validity (global rules preserved; no new thresholds).
        if any(not isinstance(ts, (int, float)) or isinstance(ts, bool) for ts in timestamps):
            base["reasons"].append("non_increasing_timestamps")
            base["error_kind"] = "fatal"
            return False, [], base
        if len(set(timestamps)) != n:
            base["reasons"].append("duplicate_timestamps")
            base["error_kind"] = "fatal"
            return False, [], base
        if any(timestamps[i] >= timestamps[i + 1] for i in range(n - 1)):
            base["reasons"].append("timestamps_not_increasing")
            base["error_kind"] = "fatal"
            return False, [], base

        if n:
            base["latest_raw_timestamp"] = float(timestamps[-1])

        # Per-row validation. A faulty row is rejected individually; valid rows
        # before and after it are preserved. Missing values are never padded.
        market_data: List[MarketData] = []
        rejection_counts: Dict[str, int] = {}
        last_valid_ts = None

        for i in range(n):
            o = open_values[i]
            h = high_values[i]
            l = low_values[i]
            c = close_values[i]
            v = volume_values[i]

            reasons = set()

            if None in (o, h, l, c, v):
                reasons.add("incomplete_null_row")
            else:
                if not all(isinstance(x, (int, float)) and not isinstance(x, bool)
                           for x in (o, h, l, c, v)):
                    reasons.add("non_numeric_or_infinite")
                elif any(isinstance(x, float) and (math.isinf(x) or math.isnan(x))
                         for x in (o, h, l, c, v)):
                    reasons.add("non_numeric_or_infinite")
                else:
                    if v < 0:
                        reasons.add("negative_volume")
                    if h < o or h < l or h < c or l > o or l > h or l > c:
                        reasons.add("ohlc_inconsistency")

            if reasons:
                for reason in reasons:
                    rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
                continue

            # volume=0 is a valid value; preserve it exactly.
            market_data.append(
                MarketData(
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=float(v),
                    timestamp=datetime.fromtimestamp(float(timestamps[i]), tz=timezone.utc),
                )
            )
            last_valid_ts = float(timestamps[i])

        base["rejection_reasons"] = dict(rejection_counts)
        base["valid_rows"] = len(market_data)
        base["rejected_rows"] = n - len(market_data)
        if last_valid_ts is not None:
            base["latest_valid_timestamp"] = last_valid_ts

        if base["valid_rows"] == 0:
            base["reasons"].append("no_complete_rows")
            base["error_kind"] = "row_rejects" if base["rejected_rows"] else "fatal"
            return False, [], base

        base["error_kind"] = "row_rejects" if base["rejected_rows"] else "none"
        base["accepted"] = True
        return True, market_data, base
