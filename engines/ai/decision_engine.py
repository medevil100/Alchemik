"""
Decision Engine for the AI Engine.

This module is responsible for combining data from the Technical Analyzer and News Analyzer
into a unified format for the Prompt Builder. It does not interpret the data or make
investment decisions.

ETAP 1: MarketEvent is now the canonical input contract.
process_data(dict) is retained as a backward-compatible adapter.
"""

import datetime
from typing import Dict, Any, List, Optional
from data.models.ai_signal import AISignal
from data.models.analysis_result import AnalysisResult
from data.models.market_event import MarketEvent
from data.models.pipeline_decision import PipelineDecision
from data.models.event_enums import PriorityLevel, SignalTiming
from engines.technical import TechnicalEngine
from engines.news import NewsPipeline


class DecisionEngine:
    """Combines technical and news analysis results for the AI Engine."""

    def __init__(self):
        """Initialize the DecisionEngine with instances of TechnicalEngine and NewsPipeline."""
        self.technical_engine = TechnicalEngine()
        self.news_pipeline = NewsPipeline(filter_config=None)

    # ------------------------------------------------------------------
    # Shared AISignal factory (single logic, used by all paths)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_aisignal(
        ticker: str,
        event_type: str,
        technical_keys: list,
        news_count: int,
        tavily_context: Optional[dict] = None,
        signal_timing: Optional[SignalTiming] = None,
    ) -> AISignal:
        """
        Build a placeholder AISignal — the single factory for all execution paths.

        Args:
            ticker: Instrument ticker or placeholder string.
            event_type: Event type or "legacy" for backward-compat path.
            technical_keys: Names of available technical indicators.
            news_count: Number of news items available (0 if none).
            tavily_context: Optional Tavily search context dict
                (from MarketEvent.tavily_context after KROK 4A).
            signal_timing: Optional SignalTiming class from MarketEvent.

        Returns:
            AISignal with placeholder confidence and generated reasoning.
        """
        technical_desc = ", ".join(technical_keys) if technical_keys else "none"
        reasoning_parts = [
            f"MarketEvent [{ticker}]: {event_type}.",
            f"Technical indicators: {technical_desc}.",
            f"News items: {news_count}.",
        ]

        # Append SignalTiming information when present
        if signal_timing is not None:
            reasoning_parts.append(
                f"Signal timing: {signal_timing.value}."
            )

        # Append Tavily section only when context is present and non-empty
        tavily_text = DecisionEngine._format_tavily_context(tavily_context)
        if tavily_text:
            reasoning_parts.append(tavily_text)

        return AISignal(
            signal_type="combined_analysis",
            confidence=0.0,  # Placeholder — actual confidence in future stages
            generated_at=datetime.datetime.now(),
            reasoning=" ".join(reasoning_parts),
        )

    # ------------------------------------------------------------------
    # Tavily context formatter
    # ------------------------------------------------------------------

    @staticmethod
    def _format_tavily_context(tavily_context: Optional[dict]) -> str:
        """Format Tavily search context for inclusion in AI reasoning.

        Produces a concise, deterministic string summarising the
        external search results.  Returns an empty string when
        *tavily_context* is ``None``, empty, or has no usable results.

        The formatted text explicitly labels Tavily data as an external
        informational context — distinct from Yahoo Finance market data
        (per docs/FILOZOFIA_ALCHEMIKA.md).

        Args:
            tavily_context: Dict from MarketEvent.tavily_context
                (shape: ``{query, results_count, top_results, sentiment}``)
                or ``None``.

        Returns:
            A formatted string ready for embedding in reasoning, or
            an empty string when there is nothing to report.
        """
        if not isinstance(tavily_context, dict) or not tavily_context:
            return ""

        query = tavily_context.get("query")
        results_count = tavily_context.get("results_count", 0)
        top_results = tavily_context.get("top_results")
        sentiment = tavily_context.get("sentiment")

        if not isinstance(top_results, (list, tuple)) or not top_results:
            return ""

        # === Build Tavily section ===
        parts: list[str] = []
        parts.append("Tavily external context:")

        if query and isinstance(query, str) and query.strip():
            parts.append(f"Query: {query.strip()}.")
        if isinstance(results_count, (int, float)):
            parts.append(f"Found: {int(results_count)} result(s).")

        for idx, item in enumerate(top_results, start=1):
            if not isinstance(item, dict):
                continue
            item_lines: list[str] = []

            title = item.get("title")
            if isinstance(title, str) and title.strip():
                item_lines.append(f"  [{idx}] {title.strip()}")

            pub_date = item.get("published_date")
            if isinstance(pub_date, str) and pub_date.strip():
                item_lines.append(f"      Date: {pub_date.strip()}")

            url = item.get("url")
            if isinstance(url, str) and url.strip():
                item_lines.append(f"      URL: {url.strip()}")

            score = item.get("score")
            if isinstance(score, (int, float)):
                item_lines.append(f"      Relevance: {score:.2f}")

            content = item.get("content")
            if isinstance(content, str) and content.strip():
                # Limit content to 500 characters to keep reasoning compact
                snippet = content.strip()[:500]
                item_lines.append(f"      Content: {snippet}")

            if item_lines:
                parts.extend(item_lines)

        if sentiment is not None and isinstance(sentiment, (int, float)):
            parts.append(f"Sentiment: {sentiment:.2f}")

        return " | ".join(parts)

    # ------------------------------------------------------------------
    # Canonical entry point — ETAP 1
    # ------------------------------------------------------------------

    def process_event(self, event: MarketEvent) -> AISignal:
        """
        Process a MarketEvent — the canonical entry point for the ALCHEMIK pipeline.

        Reads detection fields and technical_context from the MarketEvent and
        produces an AISignal via the shared _build_aisignal factory.

        Args:
            event: A MarketEvent with at minimum identification, detection,
                   and technical_context fields set.

        Returns:
            AISignal: Combined data for the Prompt Builder (placeholder in ETAP 1).

        Raises:
            RuntimeError: If processing fails due to missing required context.
        """
        try:
            technical = event.technical_context or {}
            news_count = len(event.news_context) if event.news_context else 0
            tavily_context = getattr(event, 'tavily_context', None)
            return self._build_aisignal(
                ticker=event.ticker,
                event_type=event.event_type,
                technical_keys=list(technical.keys()),
                news_count=news_count,
                tavily_context=tavily_context,
                signal_timing=event.signal_timing,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to process MarketEvent: {e}")

    # ------------------------------------------------------------------
    # Backward-compatible adapter (delegates to shared factory)
    # ------------------------------------------------------------------

    def process_data(self, market_data: Dict[str, Any]) -> AISignal:
        """
        Adapter for backward compatibility.

        All execution paths converge on the shared _build_aisignal factory.
        When 'event' contains a MarketEvent, it delegates to process_event()
        which itself uses _build_aisignal.

        Args:
            market_data: Either {'event': MarketEvent} (new) or
                         {'symbol': str, 'technical': ..., 'news': ...} (legacy).

        Returns:
            AISignal: Combined data for the Prompt Builder.

        Raises:
            RuntimeError: If processing fails.
        """
        try:
            # New path: MarketEvent-based (ETAP 1)
            if 'event' in market_data:
                event = market_data['event']
                if isinstance(event, MarketEvent):
                    return self.process_event(event)

            # Legacy path: loose dict (backward compatibility)
            # Uses the same shared factory as process_event
            news_count = len(market_data.get('news', []))
            return self._build_aisignal(
                ticker=str(market_data.get('symbol', 'unknown')),
                event_type="legacy",
                technical_keys=[],
                news_count=news_count,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to process data: {e}")

    # ------------------------------------------------------------------
    # Pipeline decision — ETAP 7.4
    # ------------------------------------------------------------------

    def decide_pipeline(self, event: MarketEvent) -> PipelineDecision:
        """
        Decide which pipeline stages to execute based on quality_level.

        Implements the decision rules from ETAP 7.4, section 7.4 of
        docs/ETAP_7_PLAN.md and ETAP 9 of docs/Kontrakt_Zdarzen_Rynkowych.md.

        Rules:
            CRITICAL → News + Tavily + AI (full analysis)
            HIGH     → News + AI (Tavily optional)
            MEDIUM   → News only
            LOW      → archive only (no analysis)
            IGNORE   → stop processing (duplicate)

        Args:
            event: A MarketEvent with quality_level set by QualityEngine.

        Returns:
            PipelineDecision with flags for each pipeline stage.

        Raises:
            RuntimeError: If the event has no quality_level set.
        """
        try:
            ql = event.quality_level
        except AttributeError:
            raise RuntimeError(
                "MarketEvent has no quality_level — "
                "QualityEngine must run before DecisionEngine"
            )

        if ql == PriorityLevel.CRITICAL:
            return PipelineDecision(
                run_news=True,
                run_tavily=True,
                run_ai=True,
                reason=(
                    f"CRITICAL — pełna analiza: "
                    f"News + Tavily + AI dla {event.ticker} ({event.event_type})"
                ),
            )
        elif ql == PriorityLevel.HIGH:
            return PipelineDecision(
                run_news=True,
                run_tavily=False,
                run_ai=True,
                reason=(
                    f"HIGH — analiza: "
                    f"News + AI dla {event.ticker} ({event.event_type})"
                ),
            )
        elif ql == PriorityLevel.MEDIUM:
            return PipelineDecision(
                run_news=True,
                run_tavily=False,
                run_ai=False,
                reason=(
                    f"MEDIUM — tylko News dla {event.ticker} ({event.event_type})"
                ),
            )
        elif ql == PriorityLevel.LOW:
            return PipelineDecision(
                run_news=False,
                run_tavily=False,
                run_ai=False,
                reason=(
                    f"LOW — tylko archiwizacja dla {event.ticker} ({event.event_type})"
                ),
            )
        elif ql == PriorityLevel.IGNORE:
            return PipelineDecision(
                run_news=False,
                run_tavily=False,
                run_ai=False,
                reason=(
                    f"IGNORE — duplikat dla {event.ticker} ({event.event_type})"
                ),
            )
        else:
            # Unknown quality_level — treat as IGNORE (safety default)
            return PipelineDecision(
                run_news=False,
                run_tavily=False,
                run_ai=False,
                reason=f"UNKNOWN quality_level={ql} — przerwanie",
            )

    def __repr__(self) -> str:
        return "<DecisionEngine>"
