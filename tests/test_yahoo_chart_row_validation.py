# -*- coding: utf-8 -*-
"""ALCHEMIK — Krok 2/8 — RED: wierszowa walidacja YahooChartProvider."""
from __future__ import annotations

import unittest

from data.yahoo.yahoo_session import FetchResult, OutcomeKind
from application.providers.yahoo_chart_provider import YahooChartProvider


def _meta(symbol):
    return {"symbol": symbol, "instrumentType": "EQUITY",
            "currency": "PLN", "exchangeName": "WSE"}


def _chart(ts, o, h, l, c, v, meta=None, symbol="AAA.WA"):
    return FetchResult(
        kind=OutcomeKind.SUCCESS_WITH_DATA,
        data={"variant": "daily", "http_status": 200,
              "captured_at": "2026-08-18T00:00:00+00:00",
              "meta": meta or _meta(symbol),
              "timestamp": ts, "open": o, "high": h, "low": l,
              "close": c, "volume": v, "events": {}},
        message=None,
    )


def _ts(n, start=1690000000):
    return list(range(start, start + n))


class FakeChartSession:
    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    def fetch_chart(self, symbol, variant="daily"):
        self.calls.append((symbol, variant))
        return self._results.pop(0)


def _scan(result):
    session = FakeChartSession([result])
    provider = YahooChartProvider(session)
    output = provider.scan(["AAA.WA"])
    return output, provider.last_scan[0]


class TestRowValidationPart1(unittest.TestCase):
    def test_null_in_open_rejects_only_that_row(self):
        n = 250
        ts = _ts(n)
        o = [1.0] * n
        o[100] = None
        result = _chart(ts, o, [1.5] * n, [0.5] * n, [1.1] * n, [10] * n)
        output, diag = _scan(result)
        self.assertEqual(len(output), 1)
        self.assertEqual(len(output[0]["data"]), 249)
        self.assertTrue(diag["accepted"])
        self.assertEqual(diag["valid_rows"], 249)
        self.assertEqual(diag["rejected_rows"], 1)
        self.assertEqual(diag["rejection_reasons"].get("incomplete_null_row"), 1)

    def test_null_in_each_ohlcv_field_rejects_only_that_row(self):
        for field_idx in (0, 1, 2, 3, 4):
            n = 5
            ts = _ts(n)
            arrays = [[1.0] * n, [1.5] * n, [0.5] * n, [1.1] * n, [10] * n]
            arrays[field_idx][3] = None
            result = _chart(ts, arrays[0], arrays[1], arrays[2],
                            arrays[3], arrays[4])
            output, diag = _scan(result)
            self.assertEqual(len(output), 1, f"field {field_idx}")
            self.assertEqual(len(output[0]["data"]), 4, f"field {field_idx}")
            self.assertTrue(diag["accepted"], f"field {field_idx}")
            self.assertEqual(diag["valid_rows"], 4, f"field {field_idx}")
            self.assertEqual(diag["rejected_rows"], 1, f"field {field_idx}")

    def test_multiple_nulls_same_row_count_once(self):
        n = 5
        ts = _ts(n)
        o = [1.0] * n
        o[2] = None
        h = [1.5] * n
        h[2] = None
        v = [10] * n
        v[2] = None
        result = _chart(ts, o, h, [0.5] * n, [1.1] * n, v)
        output, diag = _scan(result)
        self.assertEqual(len(output[0]["data"]), 4)
        self.assertEqual(diag["valid_rows"], 4)
        self.assertEqual(diag["rejected_rows"], 1)

    def test_non_numeric_value_rejects_only_that_row(self):
        n = 5
        ts = _ts(n)
        o = [1.0] * n
        o[2] = "1.0"
        result = _chart(ts, o, [1.5] * n, [0.5] * n, [1.1] * n, [10] * n)
        output, diag = _scan(result)
        self.assertEqual(len(output[0]["data"]), 4)
        self.assertTrue(diag["accepted"])
        self.assertEqual(diag["valid_rows"], 4)
        self.assertEqual(diag["rejected_rows"], 1)
        self.assertEqual(diag["rejection_reasons"].get("non_numeric_or_infinite"), 1)

    def test_infinite_value_rejects_only_that_row(self):
        n = 5
        ts = _ts(n)
        c = [1.1] * n
        c[4] = float("inf")
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n, c, [10] * n)
        output, diag = _scan(result)
        self.assertEqual(len(output[0]["data"]), 4)
        self.assertEqual(diag["valid_rows"], 4)
        self.assertEqual(diag["rejected_rows"], 1)

    def test_nan_value_rejects_only_that_row(self):
        n = 5
        ts = _ts(n)
        v = [10] * n
        v[0] = float("nan")
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n, [1.1] * n, v)
        output, diag = _scan(result)
        self.assertEqual(len(output[0]["data"]), 4)
        self.assertEqual(diag["valid_rows"], 4)
        self.assertEqual(diag["rejected_rows"], 1)

    def test_negative_volume_rejects_only_that_row(self):
        n = 5
        ts = _ts(n)
        v = [10] * n
        v[1] = -1
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n, [1.1] * n, v)
        output, diag = _scan(result)
        self.assertEqual(len(output[0]["data"]), 4)
        self.assertEqual(diag["valid_rows"], 4)
        self.assertEqual(diag["rejected_rows"], 1)
        self.assertEqual(diag["rejection_reasons"].get("negative_volume"), 1)

    def test_volume_zero_remains_valid(self):
        n = 3
        ts = _ts(n)
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n,
                        [1.1] * n, [0, 100, 200])
        output, diag = _scan(result)
        volumes = [d.volume for d in output[0]["data"]]
        self.assertIn(0, volumes)
        self.assertTrue(diag["accepted"])
        self.assertEqual(diag["valid_rows"], 3)
        self.assertEqual(diag["rejected_rows"], 0)
        self.assertNotIn("negative_volume", diag["rejection_reasons"])

    def test_ohlc_violation_rejects_only_that_row(self):
        n = 5
        ts = _ts(n)
        h = [1.5] * n
        h[3] = 0.3  # high < low -> naruszenie OHLC
        result = _chart(ts, [1.0] * n, h, [0.5] * n, [1.1] * n, [10] * n)
        output, diag = _scan(result)
        self.assertEqual(len(output[0]["data"]), 4)
        self.assertEqual(diag["valid_rows"], 4)
        self.assertEqual(diag["rejected_rows"], 1)
        self.assertEqual(diag["rejection_reasons"].get("ohlc_inconsistency"), 1)

    def test_valid_rows_before_and_after_faulty_row_preserved(self):
        n = 10
        ts = _ts(n)
        c = [1.1] * n
        c[5] = None
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n, c, [10] * n)
        output, diag = _scan(result)
        data = output[0]["data"]
        self.assertEqual(len(data), 9)
        self.assertEqual(data[0].timestamp.timestamp(), ts[0])
        self.assertEqual(data[-1].timestamp.timestamp(), ts[-1])
        for md in data:
            self.assertNotEqual(md.timestamp.timestamp(), ts[5])

    def test_valid_rows_is_actual_count(self):
        n = 7
        ts = _ts(n)
        c = [1.1] * n
        c[1] = None
        c[3] = None
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n, c, [10] * n)
        output, diag = _scan(result)
        self.assertEqual(len(output[0]["data"]), 5)
        self.assertEqual(diag["valid_rows"], 5)

    def test_rejected_rows_is_actual_count(self):
        n = 7
        ts = _ts(n)
        c = [1.1] * n
        c[1] = None
        c[3] = None
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n, c, [10] * n)
        output, diag = _scan(result)
        self.assertEqual(diag["rejected_rows"], 2)

    def test_diagnostics_store_rejection_reason_counters(self):
        n = 6
        ts = _ts(n)
        c = [1.1] * n
        c[0] = None
        c[2] = None
        v = [10] * n
        v[4] = -5
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n, c, v)
        output, diag = _scan(result)
        self.assertEqual(diag["rejection_reasons"].get("incomplete_null_row"), 2)
        self.assertEqual(diag["rejection_reasons"].get("negative_volume"), 1)
        self.assertEqual(diag["rejected_rows"], 3)


class TestRowValidationPart2(unittest.TestCase):
    def test_fully_invalid_series_keeps_diagnostics(self):
        n = 5
        ts = _ts(n)
        result = _chart(ts, [None] * n, [1.5] * n, [0.5] * n,
                        [1.1] * n, [10] * n)
        output, diag = _scan(result)
        self.assertEqual(output, [])
        self.assertFalse(diag["accepted"])
        self.assertEqual(diag["valid_rows"], 0)
        self.assertEqual(diag["rejected_rows"], n)
        self.assertEqual(diag["rejection_reasons"].get("incomplete_null_row"), n)
        self.assertIn("no_complete_rows", diag["reasons"])

    def test_short_valid_history_passes(self):
        result = _chart(_ts(1), [1.0], [1.0], [1.0], [1.0], [5])
        output, diag = _scan(result)
        self.assertEqual(len(output), 1)
        self.assertEqual(len(output[0]["data"]), 1)

    def test_latest_valid_row_is_last_element(self):
        n = 8
        ts = _ts(n)
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n,
                        [1.1] * n, [10] * n)
        output, diag = _scan(result)
        self.assertEqual(output[0]["data"][-1].timestamp.timestamp(), ts[-1])

    def test_incomplete_last_candle_does_not_remove_earlier(self):
        n = 6
        ts = _ts(n)
        c = [1.1] * n
        c[-1] = None  # niepełna ostatnia świeca
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n, c, [10] * n)
        output, diag = _scan(result)
        self.assertEqual(len(output), 1)
        self.assertEqual(len(output[0]["data"]), 5)
        self.assertEqual(output[0]["data"][-1].timestamp.timestamp(), ts[-2])

    def test_price_range_not_applied_to_history(self):
        n = 5
        ts = _ts(n)
        o = [20.0, 0.05, 12.0, 1.0, 2.0]  # ceny historyczne poza 0.10–10.00
        h = [21.0, 0.06, 13.0, 1.5, 2.5]
        l = [19.0, 0.04, 11.0, 0.5, 1.5]
        c = [20.5, 0.05, 12.5, 1.1, 2.1]
        result = _chart(ts, o, h, l, c, [10] * n)
        output, diag = _scan(result)
        self.assertEqual(len(output), 1)
        self.assertEqual(len(output[0]["data"]), 5)
        self.assertTrue(diag["accepted"])

    def test_metadata_error_distinguished_from_row_error(self):
        meta = _meta("AAA.WA")
        meta["instrumentType"] = "MUTUALFUND"
        n = 5
        ts = _ts(n)
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n,
                        [1.1] * n, [10] * n, meta=meta)
        output, diag = _scan(result)
        self.assertEqual(output, [])
        self.assertFalse(diag["accepted"])
        self.assertIn("instrument_type_not_equity", diag["reasons"])
        self.assertEqual(diag["valid_rows"], 0)
        self.assertEqual(diag["rejected_rows"], 0)
        self.assertIn("fatal", diag["error_kind"])

    def test_structure_error_distinguished_from_row_error(self):
        result = FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data={"variant": "daily", "meta": _meta("AAA.WA"),
                  "timestamp": [1, 2], "open": [1.0], "high": [1.0],
                  "low": [1.0], "close": [1.0], "volume": [5], "events": {}},
            message=None,
        )
        output, diag = _scan(result)
        self.assertEqual(output, [])
        self.assertIn("length_mismatch", diag["reasons"])
        self.assertIn("fatal", diag["error_kind"])

    def test_http_error_keeps_fatal_kind(self):
        result = FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None,
                             message="HTTP 500")
        output, diag = _scan(result)
        self.assertEqual(output, [])
        self.assertIn("endpoint_not_success_with_data", diag["reasons"])
        self.assertIn("fatal", diag["error_kind"])

    def test_no_reasons_is_not_replaced_by_artificial_error(self):
        n = 3
        ts = _ts(n)
        result = _chart(ts, [1.0] * n, [1.5] * n, [0.5] * n,
                        [1.1] * n, [0, 100, 200])
        output, diag = _scan(result)
        self.assertTrue(diag["accepted"])
        self.assertEqual(diag["reasons"], [])
        self.assertEqual(diag["rejection_reasons"], {})
        self.assertEqual(diag["error_kind"], "none")


if __name__ == "__main__":
    unittest.main()
