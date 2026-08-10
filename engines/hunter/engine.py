"""
Hunter Engine - Implementation

This module is responsible for identifying and selecting the best opportunities
from the results provided by other engines.
"""
from typing import Dict, List
from datetime import datetime
from data.models.hunter_result import HunterScanResult, HunterResult


class HunterEngine:
    """
    Hunter Engine implementation.

    Args:
        config (Dict): Configuration dictionary
    """

    def __init__(self, config: Dict):
        self.config = config

    # ------------------------------------------------------------------
    # Single-instrument scoring (Hunter pojedynczego instrumentu)
    # — existing contract, untouched
    # ------------------------------------------------------------------

    def _calculate_hunter_score(self, instrument: Dict) -> HunterResult:
        """
        Calculate hunter score for a single instrument.

        Args:
            instrument (Dict): Instrument data with scoring fields.

        Returns:
            HunterResult: Result with calculated hunter score and priority.
        """
        inverted_risk = 1.0 - instrument.get("risk_score", 0)
        hunter_score = (
            instrument.get("ranking_score", 0) * self.config["ranking_weight"]
            + inverted_risk * self.config["risk_weight"]
            + instrument.get("confidence", 0) * self.config["confidence_weight"]
        )
        hunter_score = max(0.0, min(1.0, hunter_score))

        # Determine priority based on thresholds (sorted in descending order)
        priority = 3  # Default to lowest priority
        thresholds = sorted(self.config["priority_thresholds"], reverse=True)
        for threshold in thresholds:
            if hunter_score >= threshold:
                if threshold >= 0.9:
                    priority = 1
                elif threshold >= 0.7:
                    priority = 2
                elif threshold >= 0.5:
                    priority = 3
                break

        return HunterResult(
            instrument_id=instrument["instrument_id"],
            hunter_score=hunter_score,
            priority=priority,
            ranking_score=instrument.get("ranking_score", 0),
            risk_score=instrument.get("risk_score", 0),
            risk_level="",
            confidence=instrument.get("confidence", 0),
            reasons=[],
            warnings=[],
            timestamp=datetime.now(),
        )

    # ------------------------------------------------------------------
    # MarketScanner pass-through (Krok 6A)
    # ------------------------------------------------------------------

    @staticmethod
    def _is_market_scanner_candidate(instrument: Dict) -> bool:
        """Return True if *instrument* has the MarketScanner shape.

        MarketScanner candidates carry ``symbol`` and ``data`` (OHLCV).
        They never carry ``ranking_score`` / ``risk_score`` / ``confidence``
        — those values are produced later by MasterEngine.
        """
        return "data" in instrument

    @staticmethod
    def _validate_and_pass_market_scanner(
        instrument: Dict,
    ) -> HunterResult | None:
        """Validate a MarketScanner-shaped candidate and produce a
        pass-through ``HunterResult``, or return ``None`` if invalid.

        Rules:
          - ``symbol`` must be a non-empty string.
          - ``data`` must be a non-empty list.
          - All scoring fields (``hunter_score``, ``priority``,
            ``ranking_score``, ``risk_score``, ``confidence``) are ``None``
            — no artificial metrics are created.
        """
        symbol = instrument.get("symbol")
        data = instrument.get("data")
        if not isinstance(symbol, str) or not symbol.strip():
            return None
        if not isinstance(data, list) or len(data) == 0:
            return None
        return HunterResult(
            instrument_id=symbol,
            hunter_score=None,
            priority=None,
            ranking_score=None,
            risk_score=None,
            risk_level="",
            confidence=None,
            reasons=[],
            warnings=[],
            timestamp=datetime.now(),
        )

    # ------------------------------------------------------------------
    # Main scan method
    # ------------------------------------------------------------------

    def scan(self, instruments: List[Dict]) -> HunterScanResult:
        """
        Scan instruments and return qualified opportunities.

        Two input shapes are supported:

         1. **MarketScanner candidate** — ``{"symbol": str, "data": [...]}``
            (OHLCV data from Yahoo Finance via MarketScanner).
            These candidates **pass through unchanged** — no artificial
            scoring values are created.

        2. **Single-instrument scoring candidate** — ``{"instrument_id": str,
           "ranking_score": float, "risk_score": float, "confidence": float}``.
           These are filtered and scored using the existing threshold logic.

        Args:
            instruments (List[Dict]): List of instrument data dicts.

        Returns:
            HunterScanResult: Complete scan result with opportunities and stats.
        """
        opportunities = []
        analyzed = len(instruments)
        rejected = 0
        qualified = 0

        for instrument in instruments:
            # --------------------------------------------------------------
            # Shape detection: MarketScanner candidate (has "data" key)
            # --------------------------------------------------------------
            if self._is_market_scanner_candidate(instrument):
                result = self._validate_and_pass_market_scanner(instrument)
                if result is None:
                    rejected += 1
                    continue
                opportunities.append(result)
                qualified += 1
                continue

            # --------------------------------------------------------------
            # Single-instrument scoring (existing logic — untouched)
            # --------------------------------------------------------------
            if (
                instrument.get("ranking_score", 0)
                < self.config["min_ranking_score"]
                or instrument.get("risk_score", 0)
                > self.config["max_risk_score"]
                or instrument.get("confidence", 0)
                < self.config["min_confidence"]
            ):
                rejected += 1
                continue

            result = self._calculate_hunter_score(instrument)
            opportunities.append(result)
            qualified += 1

        # Sort by hunter_score (descending) and limit results.
        # MarketScanner results have hunter_score=None and sort last.
        def _sort_key(hr: HunterResult) -> float:
            return hr.hunter_score if hr.hunter_score is not None else -1.0

        opportunities.sort(key=_sort_key, reverse=True)
        if len(opportunities) > self.config["max_results"]:
            opportunities = opportunities[: self.config["max_results"]]
            rejected += len(opportunities) - self.config["max_results"]

        return HunterScanResult(
            opportunities=opportunities,
            analyzed=analyzed,
            rejected=rejected,
            qualified=min(qualified, self.config["max_results"]),
            timestamp=datetime.now(),
        )