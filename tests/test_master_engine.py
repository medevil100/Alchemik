import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from engines.master.engine import MasterEngine
from data.models import (
    FinalAnalysisResult,
    MarketData,
    Company as CompanyInfo,
    NewsItem,
    AISignal,
    RankingResult,
    RiskResult,
    HunterResult,
    AnalysisResult,
    MarketEvent,
    InstrumentType,
    EventFamily,
    PriorityLevel,
    EventOwner,
)
from data.models.pipeline_decision import PipelineDecision

class TestMasterEngine(unittest.TestCase):
    def setUp(self):
        # Mock all dependencies
        self.mock_technical_engine = Mock()
        self.mock_news_engine = Mock()
        self.mock_ai_engine = Mock()
        self.mock_ranking_engine = Mock()
        self.mock_risk_engine = Mock()
        self.mock_hunter_engine = Mock()
        self.mock_analyst_engine = Mock()
        self.mock_price_detector = Mock()
        self.mock_volume_detector = Mock()

        # Configure mock returns
        self.market_data = MarketData(
            open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1234567890
        )
        self.news_item = NewsItem(
            title="Test News",
            source="Test Source",
            publish_date=datetime.fromisoformat("2023-01-01"),
            url="http://example.com",
            summary="Test Content",
            sentiment=0.5
        )
        self.mock_technical_engine.analyze.return_value = self.market_data
        self.mock_news_engine.process.return_value = [self.news_item]
        self.mock_ai_engine.decide.return_value = AISignal(
            signal_type="BUY",
            confidence=0.9,
            generated_at=datetime.now(),
            reasoning="Test"
        )
        self.mock_ranking_engine.rank.return_value = RankingResult(
            instrument_id="TEST",
            score=0.95,
            details={}
        )
        self.mock_risk_engine.assess.return_value = RiskResult(
            instrument_id="TEST",
            risk_level="LOW",
            risk_score=0.2,
            confidence=0.9,
            risk_factors=[],
            max_position_size=1000.0,
            stop_loss=95.0,
            take_profit=110.0,
            timestamp=datetime.now()
        )
        self.mock_hunter_engine.hunt.return_value = HunterResult(
            instrument_id="TEST",
            hunter_score=0.9,
            priority=1,
            ranking_score=0.95,
            risk_score=0.2,
            risk_level="LOW",
            confidence=0.9,
            reasons=[],
            warnings=[],
            timestamp=datetime.now()
        )
        self.mock_analyst_engine.analyze.return_value = AnalysisResult(
            company=CompanyInfo(
                symbol="TEST",
                name="Test Company",
                sector="Test Sector"
            ),
            market_data=[self.market_data],
            news=[self.news_item],
            signals=[AISignal(
                signal_type="BUY",
                confidence=0.9,
                generated_at=datetime.now(),
                reasoning="Test"
            )],
            generated_at=datetime.now()
        )

        # Configure mock detectors
        self.mock_price_detector.detect.return_value = []
        self.mock_volume_detector.detect.return_value = []

        # Initialize MasterEngine with mocked dependencies
        self.master_engine = MasterEngine(
            technical_engine=self.mock_technical_engine,
            news_engine=self.mock_news_engine,
            ai_engine=self.mock_ai_engine,
            ranking_engine=self.mock_ranking_engine,
            risk_engine=self.mock_risk_engine,
            hunter_engine=self.mock_hunter_engine,
            analyst_engine=self.mock_analyst_engine,
            price_detector=self.mock_price_detector,
            volume_detector=self.mock_volume_detector,
        )

    def test_run_analysis_sequence(self):
        symbol = "TEST"
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
            MarketData(open=102.0, high=108.0, low=101.0, close=107.0, volume=2000000, timestamp=2),
        ]
        self.mock_technical_engine.analyze.return_value = ohlcv_data
        result = self.master_engine.run_analysis(symbol, ohlcv_data=ohlcv_data)

        # Verify technical engine was called with the OHLCV data
        self.mock_technical_engine.analyze.assert_called_once_with(ohlcv_data)
        # News may not be called (empty market_events → no events to analyze)
        self.mock_ai_engine.process_data.assert_called_once()
        self.mock_ranking_engine.calculate_ranking.assert_called_once()
        self.mock_risk_engine.assess_risk.assert_called_once()
        self.mock_hunter_engine.scan.assert_called_once()
        self.mock_analyst_engine.generate_analysis.assert_called_once()

        # Verify the result is a FinalAnalysisResult
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_invalid_symbol(self):
        with self.assertRaises(ValueError):
            self.master_engine.run_analysis("")
        with self.assertRaises(ValueError):
            self.master_engine.run_analysis(123)

    def test_error_handling(self):
        """Technical Engine error propagates when ohlcv_data is provided."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]
        self.mock_technical_engine.analyze.side_effect = Exception("Technical Engine Error")
        with self.assertRaises(Exception) as context:
            self.master_engine.run_analysis("TEST", ohlcv_data=ohlcv_data)
        self.assertIn("Technical Engine Error", str(context.exception))

    def test_run_analysis_no_ohlcv_creates_empty_result(self):
        """Test that run_analysis creates an empty AnalysisResult when no ohlcv_data is provided."""
        result = self.master_engine.run_analysis("TEST")

        # TechnicalEngine.analyze should NOT be called when no ohlcv_data
        self.mock_technical_engine.analyze.assert_not_called()

        # Old pipeline still works (News may not be called — no events)
        self.mock_ai_engine.process_data.assert_called_once()
        self.mock_ranking_engine.calculate_ranking.assert_called_once()
        self.mock_risk_engine.assess_risk.assert_called_once()
        self.mock_hunter_engine.scan.assert_called_once()
        self.mock_analyst_engine.generate_analysis.assert_called_once()
        self.assertIsInstance(result, FinalAnalysisResult)

        # Verify detectors were NOT called (no market_data)
        self.mock_price_detector.detect.assert_not_called()
        self.mock_volume_detector.detect.assert_not_called()

    def test_run_detectors_calls_both_detectors(self):
        """Test that run_detectors() calls PriceDetector and VolumeDetector."""
        symbol = "TEST"
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
            MarketData(open=102.0, high=108.0, low=101.0, close=107.0, volume=2000000, timestamp=2),
        ]
        events = self.master_engine.run_detectors(
            ticker=symbol,
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=ohlcv_data,
        )

        self.mock_price_detector.detect.assert_called_once_with(
            ticker=symbol,
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=ohlcv_data,
        )
        self.mock_volume_detector.detect.assert_called_once_with(
            ticker=symbol,
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=ohlcv_data,
        )
        self.assertIsInstance(events, list)

    def test_run_detectors_combines_results(self):
        """Test that run_detectors() combines events from both detectors."""
        mock_price_event = MagicMock(spec=MarketEvent)
        mock_volume_event = MagicMock(spec=MarketEvent)

        self.mock_price_detector.detect.return_value = [mock_price_event]
        self.mock_volume_detector.detect.return_value = [mock_volume_event]

        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
            MarketData(open=102.0, high=108.0, low=101.0, close=107.0, volume=2000000, timestamp=2),
        ]
        events = self.master_engine.run_detectors(
            ticker="TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=ohlcv_data,
        )

        self.assertEqual(len(events), 2)
        self.assertIn(mock_price_event, events)
        self.assertIn(mock_volume_event, events)

    def test_run_detectors_empty_data(self):
        """Test that run_detectors() returns empty list when both detectors return empty."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=100.0, volume=1000000, timestamp=1),
            MarketData(open=100.0, high=105.0, low=95.0, close=100.0, volume=1000000, timestamp=2),
        ]
        events = self.master_engine.run_detectors(
            ticker="TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=ohlcv_data,
        )
        self.assertEqual(len(events), 0)

    def test_run_detectors_passes_correct_ticker(self):
        """Test that the correct ticker is passed to both detectors."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
            MarketData(open=102.0, high=108.0, low=101.0, close=107.0, volume=2000000, timestamp=2),
        ]
        self.master_engine.run_detectors(
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=ohlcv_data,
        )

        self.mock_price_detector.detect.assert_called_once_with(
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=ohlcv_data,
        )
        self.mock_volume_detector.detect.assert_called_once_with(
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=ohlcv_data,
        )

    def test_run_analysis_detectors_called_with_ohlcv_data(self):
        """Test that run_analysis calls detectors with market_data from technical result when ohlcv_data is passed."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
            MarketData(open=102.0, high=108.0, low=101.0, close=107.0, volume=2000000, timestamp=2),
        ]

        # Technical result has market_data attribute
        class TechnicalResultWithData:
            def __init__(self, data):
                self.market_data = data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData(ohlcv_data)
        result = self.master_engine.run_analysis("TEST", ohlcv_data=ohlcv_data)

        # Verify technical engine was called
        self.mock_technical_engine.analyze.assert_called_once_with(ohlcv_data)

        # Verify detectors were called
        self.mock_price_detector.detect.assert_called_once()
        self.mock_volume_detector.detect.assert_called_once()

        # Verify the old pipeline still works
        self.mock_ai_engine.process_data.assert_called_once()
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_run_analysis_pipeline_unchanged(self):
        """Test that the existing pipeline still works without ohlcv_data."""
        result = self.master_engine.run_analysis("TEST")

        # Without ohlcv_data, technical_engine is NOT called
        self.mock_technical_engine.analyze.assert_not_called()

        # Old pipeline still works
        self.mock_ai_engine.process_data.assert_called_once()
        self.mock_ranking_engine.calculate_ranking.assert_called_once()
        self.mock_risk_engine.assess_risk.assert_called_once()
        self.mock_hunter_engine.scan.assert_called_once()
        self.mock_analyst_engine.generate_analysis.assert_called_once()
        self.assertIsInstance(result, FinalAnalysisResult)

        # Verify detectors were NOT called (no market_data)
        self.mock_price_detector.detect.assert_not_called()
        self.mock_volume_detector.detect.assert_not_called()

    # ------------------------------------------------------------------
    # Tests: Market and instrument_type propagation with OHLCV data
    # ------------------------------------------------------------------

    def test_run_analysis_passes_market_to_detectors(self):
        """Test that market is passed correctly to detectors through run_analysis."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        self.master_engine.run_analysis("TEST", market="GPW", instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=ohlcv_data)

        # Verify both detectors received the correct market
        self.mock_price_detector.detect.assert_called_once()
        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["market"], "GPW")

        self.mock_volume_detector.detect.assert_called_once()
        volume_kwargs = self.mock_volume_detector.detect.call_args.kwargs
        self.assertEqual(volume_kwargs["market"], "GPW")

    def test_run_analysis_passes_instrument_type_to_detectors(self):
        """Test that instrument_type is passed correctly to detectors through run_analysis."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        self.master_engine.run_analysis("TEST", market="GPW", instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=ohlcv_data)

        # Verify both detectors received the correct instrument_type
        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["instrument_type"], InstrumentType.STOCK_GPW)

        volume_kwargs = self.mock_volume_detector.detect.call_args.kwargs
        self.assertEqual(volume_kwargs["instrument_type"], InstrumentType.STOCK_GPW)

    def test_usa_instrument_passes_correct_values(self):
        """Test that USA instrument passes NYSE and STOCK_USA."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        self.master_engine.run_analysis("TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA, ohlcv_data=ohlcv_data)

        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["market"], "NYSE")
        self.assertEqual(price_kwargs["instrument_type"], InstrumentType.STOCK_USA)

        volume_kwargs = self.mock_volume_detector.detect.call_args.kwargs
        self.assertEqual(volume_kwargs["market"], "NYSE")
        self.assertEqual(volume_kwargs["instrument_type"], InstrumentType.STOCK_USA)

    def test_gpw_instrument_passes_correct_values(self):
        """Test that GPW instrument passes GPW and STOCK_GPW."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        self.master_engine.run_analysis("XYZ.WA", market="GPW", instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=ohlcv_data)

        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["market"], "GPW")
        self.assertEqual(price_kwargs["instrument_type"], InstrumentType.STOCK_GPW)

        volume_kwargs = self.mock_volume_detector.detect.call_args.kwargs
        self.assertEqual(volume_kwargs["market"], "GPW")
        self.assertEqual(volume_kwargs["instrument_type"], InstrumentType.STOCK_GPW)

    def test_no_hardcoded_nyse(self):
        """Test that run_analysis does NOT default to NYSE."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        # Call with NASDAQ to verify no NYSE default
        self.master_engine.run_analysis("TEST", market="NASDAQ", instrument_type=InstrumentType.STOCK_USA, ohlcv_data=ohlcv_data)

        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["market"], "NASDAQ")
        self.assertNotEqual(price_kwargs["market"], "NYSE")

    def test_no_hardcoded_stock_usa(self):
        """Test that run_analysis does NOT default to STOCK_USA."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        # Call with STOCK_GPW to verify no STOCK_USA default
        self.master_engine.run_analysis("TEST", market="GPW", instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=ohlcv_data)

        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["instrument_type"], InstrumentType.STOCK_GPW)
        self.assertNotEqual(price_kwargs["instrument_type"], InstrumentType.STOCK_USA)

    def test_events_out_receives_detected_events(self):
        """Test that events_out parameter collects MarketEvents from detectors."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()

        base_time = datetime(2026, 7, 27, 12, 0, 0)
        mock_price_event = MagicMock(spec=MarketEvent)
        mock_price_event.ticker = "TEST"
        mock_price_event.timestamp_utc = base_time
        mock_price_event.event_id = "price-uuid"
        mock_price_event.event_family = EventFamily.PRICE
        mock_price_event.priority_raw = PriorityLevel.HIGH
        mock_price_event.confidence_level = 0.8
        mock_price_event.market = "NYSE"
        mock_price_event.instrument_type = InstrumentType.STOCK_USA
        mock_price_event.event_type = "PRICE_SURGE"
        mock_price_event.is_composite = False
        mock_price_event.composite_events = []

        mock_volume_event = MagicMock(spec=MarketEvent)
        mock_volume_event.ticker = "TEST"
        mock_volume_event.timestamp_utc = base_time
        mock_volume_event.event_id = "volume-uuid"
        mock_volume_event.event_family = EventFamily.VOLUME
        mock_volume_event.priority_raw = PriorityLevel.HIGH
        mock_volume_event.confidence_level = 0.9
        mock_volume_event.market = "NYSE"
        mock_volume_event.instrument_type = InstrumentType.STOCK_USA
        mock_volume_event.event_type = "VOLUME_SPIKE"
        mock_volume_event.is_composite = False
        mock_volume_event.composite_events = []

        self.mock_price_detector.detect.return_value = [mock_price_event]
        self.mock_volume_detector.detect.return_value = [mock_volume_event]

        events_out = []
        result = self.master_engine.run_analysis(
            "TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out,
            ohlcv_data=ohlcv_data,
        )

        # events_out contains originals (2) + composite (1) = 3
        self.assertEqual(len(events_out), 3)
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_events_out_empty_when_no_market_data(self):
        """Test that events_out remains empty when no market_data is available."""
        result = self.master_engine.run_analysis(
            "TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
        )

        self.mock_technical_engine.analyze.assert_not_called()
        self.mock_price_detector.detect.assert_not_called()
        self.mock_volume_detector.detect.assert_not_called()
        self.assertIsInstance(result, FinalAnalysisResult)

    # ------------------------------------------------------------------
    # Tests: ComposerEngine integration (KROK 2A)
    # ------------------------------------------------------------------

    def test_composer_not_called_when_no_events(self):
        """KROK 2A Test 1: No MarketEvent → ComposerEngine is not called."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()

        # Both detectors return empty — no events
        self.mock_price_detector.detect.return_value = []
        self.mock_volume_detector.detect.return_value = []

        events_out = []
        result = self.master_engine.run_analysis(
            "TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out,
            ohlcv_data=ohlcv_data,
        )

        # No events detected → events_out stays empty
        self.assertEqual(len(events_out), 0)
        self.assertIsInstance(result, FinalAnalysisResult)
        # Verify AI was not called with events (fallback path)
        self.mock_ai_engine.process_data.assert_called_once()

    def test_single_event_passes_through_composer(self):
        """KROK 2A Test 2: One MarketEvent → ComposerEngine is called,
        event passes through unchanged."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()

        base_time = datetime(2026, 7, 27, 12, 0, 0)
        mock_price_event = MagicMock(spec=MarketEvent)
        mock_price_event.ticker = "TEST"
        mock_price_event.timestamp_utc = base_time
        mock_price_event.event_id = "single-uuid"
        mock_price_event.event_family = EventFamily.PRICE
        mock_price_event.priority_raw = PriorityLevel.HIGH
        mock_price_event.confidence_level = 0.8
        mock_price_event.market = "NYSE"
        mock_price_event.instrument_type = InstrumentType.STOCK_USA
        mock_price_event.event_type = "PRICE_SURGE"
        mock_price_event.is_composite = False
        mock_price_event.composite_events = []

        self.mock_price_detector.detect.return_value = [mock_price_event]
        self.mock_volume_detector.detect.return_value = []

        events_out = []
        result = self.master_engine.run_analysis(
            "TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out,
            ohlcv_data=ohlcv_data,
        )

        # Single event → no composite created, just 1 event
        self.assertEqual(len(events_out), 1)
        self.assertIn(mock_price_event, events_out)
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_compatible_events_create_composite(self):
        """KROK 2A Test 3: Several compatible MarketEvents →
        ComposerEngine returns CompositeEvent alongside originals."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()

        base_time = datetime(2026, 7, 27, 12, 0, 0)

        mock_price_event = MagicMock(spec=MarketEvent)
        mock_price_event.ticker = "TEST"
        mock_price_event.timestamp_utc = base_time
        mock_price_event.event_id = "price-uuid"
        mock_price_event.event_family = EventFamily.PRICE
        mock_price_event.priority_raw = PriorityLevel.HIGH
        mock_price_event.confidence_level = 0.8
        mock_price_event.market = "NYSE"
        mock_price_event.instrument_type = InstrumentType.STOCK_USA
        mock_price_event.event_type = "PRICE_SURGE"
        mock_price_event.is_composite = False
        mock_price_event.composite_events = []

        mock_volume_event = MagicMock(spec=MarketEvent)
        mock_volume_event.ticker = "TEST"
        mock_volume_event.timestamp_utc = base_time
        mock_volume_event.event_id = "volume-uuid"
        mock_volume_event.event_family = EventFamily.VOLUME
        mock_volume_event.priority_raw = PriorityLevel.HIGH
        mock_volume_event.confidence_level = 0.9
        mock_volume_event.market = "NYSE"
        mock_volume_event.instrument_type = InstrumentType.STOCK_USA
        mock_volume_event.event_type = "VOLUME_SPIKE"
        mock_volume_event.is_composite = False
        mock_volume_event.composite_events = []

        self.mock_price_detector.detect.return_value = [mock_price_event]
        self.mock_volume_detector.detect.return_value = [mock_volume_event]

        events_out = []
        result = self.master_engine.run_analysis(
            "TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out,
            ohlcv_data=ohlcv_data,
        )

        # 2 originals + 1 composite = 3 events
        self.assertEqual(len(events_out), 3)

        # Verify originals are present
        self.assertIn(mock_price_event, events_out)
        self.assertIn(mock_volume_event, events_out)

        # Verify a composite event exists
        composites = [e for e in events_out if not isinstance(e, MagicMock) or
                      (hasattr(e, 'is_composite') and e.is_composite)]
        # Find the real MarketEvent composite (not mocks)
        real_composites = [
            e for e in events_out
            if not any(e is m for m in [mock_price_event, mock_volume_event])
        ]
        self.assertEqual(len(real_composites), 1)
        ce = real_composites[0]
        self.assertTrue(ce.is_composite)
        self.assertEqual(len(ce.composite_events), 2)
        self.assertIn("price-uuid", ce.composite_events)
        self.assertIn("volume-uuid", ce.composite_events)
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_incompatible_events_no_false_composite(self):
        """KROK 2A Test 4: Several incompatible MarketEvents →
        no incorrect CompositeEvent is created."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
        ]

        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()

        base_time = datetime(2026, 7, 27, 12, 0, 0)

        # PRICE and CORPORATE are incompatible families
        mock_price_event = MagicMock(spec=MarketEvent)
        mock_price_event.ticker = "TEST"
        mock_price_event.timestamp_utc = base_time
        mock_price_event.event_id = "price-uuid"
        mock_price_event.event_family = EventFamily.PRICE
        mock_price_event.priority_raw = PriorityLevel.HIGH
        mock_price_event.confidence_level = 0.8
        mock_price_event.market = "NYSE"
        mock_price_event.instrument_type = InstrumentType.STOCK_USA
        mock_price_event.event_type = "PRICE_SURGE"
        mock_price_event.is_composite = False
        mock_price_event.composite_events = []

        mock_corporate_event = MagicMock(spec=MarketEvent)
        mock_corporate_event.ticker = "TEST"
        mock_corporate_event.timestamp_utc = base_time
        mock_corporate_event.event_id = "corp-uuid"
        mock_corporate_event.event_family = EventFamily.CORPORATE
        mock_corporate_event.priority_raw = PriorityLevel.HIGH
        mock_corporate_event.confidence_level = 0.85
        mock_corporate_event.market = "NYSE"
        mock_corporate_event.instrument_type = InstrumentType.STOCK_USA
        mock_corporate_event.event_type = "M_AND_A_ANNOUNCEMENT"
        mock_corporate_event.is_composite = False
        mock_corporate_event.composite_events = []

        # Use price_detector for price, volume_detector for corporate-event mock
        self.mock_price_detector.detect.return_value = [mock_price_event]
        self.mock_volume_detector.detect.return_value = [mock_corporate_event]

        events_out = []
        result = self.master_engine.run_analysis(
            "TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out,
            ohlcv_data=ohlcv_data,
        )

        # Only 2 originals — no composite (PRICE + CORPORATE incompatible)
        self.assertEqual(len(events_out), 2)
        self.assertIn(mock_price_event, events_out)
        self.assertIn(mock_corporate_event, events_out)

        # Verify no composite was created
        real_events = [
            e for e in events_out
            if not any(e is m for m in [mock_price_event, mock_corporate_event])
        ]
        self.assertEqual(len(real_events), 0,
                         "No real (non-mock) events should exist — composite not created")

        self.assertIsInstance(result, FinalAnalysisResult)

    def test_old_pipeline_unchanged_with_new_params(self):
        """Test that old pipeline is unchanged when new params are used."""
        result = self.master_engine.run_analysis(
            "TEST",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
        )

        # Without ohlcv_data, technical engine is NOT called
        self.mock_technical_engine.analyze.assert_not_called()

        # Old pipeline still works
        self.mock_ai_engine.process_data.assert_called_once()
        self.mock_ranking_engine.calculate_ranking.assert_called_once()
        self.mock_risk_engine.assess_risk.assert_called_once()
        self.mock_hunter_engine.scan.assert_called_once()
        self.mock_analyst_engine.generate_analysis.assert_called_once()
        self.assertIsInstance(result, FinalAnalysisResult)

    # ------------------------------------------------------------------
    # Tests: QualityEngine integration (KROK 2B.2)
    # ------------------------------------------------------------------

class TestMasterEngineQualityIntegration(unittest.TestCase):
    """Integration tests for QualityEngine in the pipeline (KROK 2B)."""

    def setUp(self):
        self.mock_technical_engine = Mock()
        self.mock_news_engine = Mock()
        self.mock_ai_engine = Mock()
        self.mock_ranking_engine = Mock()
        self.mock_risk_engine = Mock()
        self.mock_hunter_engine = Mock()
        self.mock_analyst_engine = Mock()
        self.mock_price_detector = Mock()
        self.mock_volume_detector = Mock()
        self.mock_quality_engine = Mock()
        self.mock_composer_engine = Mock()

        # Default: detectors return nothing
        self.mock_price_detector.detect.return_value = []
        self.mock_volume_detector.detect.return_value = []

        # Mock composer — pass-through (returns same list)
        self.mock_composer_engine.compose.side_effect = lambda events: events

        # Mock quality — pass-through (returns same event)
        self.mock_quality_engine.assess.side_effect = lambda ev: ev

        # Standard mock returns for pipeline
        self.news_item = NewsItem(
            title="Test News", source="Test Source",
            publish_date=datetime.fromisoformat("2023-01-01"),
            url="http://example.com", summary="Test Content", sentiment=0.5,
        )
        self.mock_news_engine.process.return_value = [self.news_item]
        self.mock_ai_engine.process_data.return_value = AISignal(
            signal_type="BUY", confidence=0.9,
            generated_at=datetime.now(), reasoning="Test",
        )
        # ranking, risk, hunter, analyst mocks auto-create return values
        # (same pattern as TestMasterEngine)

    def _make_master_engine(self):
        return MasterEngine(
            technical_engine=self.mock_technical_engine,
            news_engine=self.mock_news_engine,
            ai_engine=self.mock_ai_engine,
            ranking_engine=self.mock_ranking_engine,
            risk_engine=self.mock_risk_engine,
            hunter_engine=self.mock_hunter_engine,
            analyst_engine=self.mock_analyst_engine,
            price_detector=self.mock_price_detector,
            volume_detector=self.mock_volume_detector,
            composer_engine=self.mock_composer_engine,
            quality_engine=self.mock_quality_engine,
        )

    def test_quality_not_called_when_no_events(self):
        """KROK 2B Test 1: QualityEngine.assess() not called for empty list."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0,
                       volume=1000000, timestamp=1),
        ]
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data
        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()

        # Both detectors return empty
        self.mock_price_detector.detect.return_value = []
        self.mock_volume_detector.detect.return_value = []

        engine = self._make_master_engine()
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # QualityEngine.assess() must NOT be called
        self.mock_quality_engine.assess.assert_not_called()
        self.assertEqual(len(events_out), 0)
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_quality_called_once_per_event(self):
        """KROK 2B Test 2: QualityEngine.assess() called once per event."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0,
                       volume=1000000, timestamp=1),
        ]
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data
        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()

        base_time = datetime(2026, 7, 28, 12, 0, 0)
        # Create 3 mock events
        mock_events = []
        for i in range(3):
            ev = MagicMock(spec=MarketEvent)
            ev.ticker = "TEST"
            ev.timestamp_utc = base_time
            ev.event_id = f"ev-{i}"
            ev.event_family = EventFamily.PRICE
            ev.priority_raw = PriorityLevel.HIGH
            ev.confidence_level = 0.8
            ev.market = "NYSE"
            ev.instrument_type = InstrumentType.STOCK_USA
            ev.event_type = "PRICE_SURGE"
            ev.is_composite = False
            ev.composite_events = []
            mock_events.append(ev)

        self.mock_price_detector.detect.return_value = mock_events
        self.mock_volume_detector.detect.return_value = []

        engine = self._make_master_engine()
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # assess() must be called exactly 3 times (once per event)
        self.assertEqual(self.mock_quality_engine.assess.call_count, 3)
        self.assertEqual(len(events_out), 3)
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_composite_event_passes_through_quality(self):
        """KROK 2B Test 3: Composite MarketEvent passes through QualityEngine."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0,
                       volume=1000000, timestamp=1),
        ]
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data
        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()

        base_time = datetime(2026, 7, 28, 12, 0, 0)
        mock_composite = MagicMock(spec=MarketEvent)
        mock_composite.ticker = "TEST"
        mock_composite.timestamp_utc = base_time
        mock_composite.event_id = "composite-uuid"
        mock_composite.event_family = EventFamily.PRICE
        mock_composite.priority_raw = PriorityLevel.HIGH
        mock_composite.confidence_level = 0.85
        mock_composite.market = "NYSE"
        mock_composite.instrument_type = InstrumentType.STOCK_USA
        mock_composite.event_type = "COMPOSITE_MULTI_EVENT"
        mock_composite.is_composite = True
        mock_composite.composite_events = ["comp-a", "comp-b"]

        self.mock_price_detector.detect.return_value = [mock_composite]
        self.mock_volume_detector.detect.return_value = []

        engine = self._make_master_engine()
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # assess() must be called with the composite event
        self.mock_quality_engine.assess.assert_called()
        # Verify the call argument was our composite mock
        called_with = self.mock_quality_engine.assess.call_args[0][0]
        self.assertTrue(called_with.is_composite)
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_events_out_receives_assessed_events(self):
        """KROK 2B Test 4: events_out receives events after QualityEngine
        assessment with quality_level already set."""
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0,
                       volume=1000000, timestamp=1),
        ]
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = ohlcv_data
        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()

        base_time = datetime(2026, 7, 28, 12, 0, 0)
        mock_event = MagicMock(spec=MarketEvent)
        mock_event.ticker = "TEST"
        mock_event.timestamp_utc = base_time
        mock_event.event_id = "assess-uuid"
        mock_event.event_family = EventFamily.PRICE
        mock_event.priority_raw = PriorityLevel.HIGH
        mock_event.confidence_level = 0.8
        mock_event.market = "NYSE"
        mock_event.instrument_type = InstrumentType.STOCK_USA
        mock_event.event_type = "PRICE_SURGE"
        mock_event.is_composite = False
        mock_event.composite_events = []

        self.mock_price_detector.detect.return_value = [mock_event]
        self.mock_volume_detector.detect.return_value = []

        engine = self._make_master_engine()
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # assess() must have been called
        self.mock_quality_engine.assess.assert_called_once()
        # events_out must contain the (mock) event
        self.assertEqual(len(events_out), 1)
        self.assertIn(mock_event, events_out)
        self.assertIsInstance(result, FinalAnalysisResult)


class TestMasterEngineDecisionIntegration(unittest.TestCase):
    """Integration tests for DecisionEngine in the pipeline (KROK 2C)."""

    def setUp(self):
        self.mock_technical_engine = Mock()
        self.mock_news_engine = Mock()
        self.mock_ai_engine = Mock()
        self.mock_ranking_engine = Mock()
        self.mock_risk_engine = Mock()
        self.mock_hunter_engine = Mock()
        self.mock_analyst_engine = Mock()
        self.mock_price_detector = Mock()
        self.mock_volume_detector = Mock()
        self.mock_quality_engine = Mock()
        self.mock_composer_engine = Mock()

        # Default: detectors return nothing
        self.mock_price_detector.detect.return_value = []
        self.mock_volume_detector.detect.return_value = []

        # Mock composer — pass-through
        self.mock_composer_engine.compose.side_effect = lambda events: events
        # Mock quality — pass-through
        self.mock_quality_engine.assess.side_effect = lambda ev: ev

        # Standard mock returns for pipeline
        self.news_item = NewsItem(
            title="Test News", source="Test Source",
            publish_date=datetime.fromisoformat("2023-01-01"),
            url="http://example.com", summary="Test Content", sentiment=0.5,
        )
        self.mock_news_engine.process.return_value = [self.news_item]
        self.mock_ai_engine.process_data.return_value = AISignal(
            signal_type="BUY", confidence=0.9,
            generated_at=datetime.now(), reasoning="Test",
        )
        # ranking, risk, hunter, analyst mocks auto-create return values

    def _make_master_engine(self):
        return MasterEngine(
            technical_engine=self.mock_technical_engine,
            news_engine=self.mock_news_engine,
            ai_engine=self.mock_ai_engine,
            ranking_engine=self.mock_ranking_engine,
            risk_engine=self.mock_risk_engine,
            hunter_engine=self.mock_hunter_engine,
            analyst_engine=self.mock_analyst_engine,
            price_detector=self.mock_price_detector,
            volume_detector=self.mock_volume_detector,
            composer_engine=self.mock_composer_engine,
            quality_engine=self.mock_quality_engine,
        )

    def _make_mock_event(self, event_id="ev-0", ticker="TEST",
                         event_family=EventFamily.PRICE):
        ev = MagicMock(spec=MarketEvent)
        ev.ticker = ticker
        ev.timestamp_utc = datetime(2026, 7, 28, 12, 0, 0)
        ev.event_id = event_id
        ev.event_family = event_family
        ev.priority_raw = PriorityLevel.HIGH
        ev.confidence_level = 0.8
        ev.market = "NYSE"
        ev.instrument_type = InstrumentType.STOCK_USA
        ev.event_type = "PRICE_SURGE"
        ev.is_composite = False
        ev.composite_events = []
        return ev

    def _setup_ohlcv(self):
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0,
                       volume=1000000, timestamp=1),
        ]
        class TechnicalResultWithData:
            def __init__(self, data):
                self.market_data = data
        self.mock_technical_engine.analyze.return_value = (
            TechnicalResultWithData(ohlcv_data))
        return ohlcv_data

    # ------------------------------------------------------------------
    # Test: decide_pipeline() called for each event
    # ------------------------------------------------------------------

    def test_decide_pipeline_called_per_event(self):
        """KROK 2C Test 1: decide_pipeline() called once per MarketEvent."""
        ohlcv_data = self._setup_ohlcv()
        mock_events = [self._make_mock_event(f"ev-{i}") for i in range(3)]
        self.mock_price_detector.detect.return_value = mock_events

        engine = self._make_master_engine()
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        self.assertEqual(self.mock_ai_engine.decide_pipeline.call_count, 3)
        self.assertIsInstance(result, FinalAnalysisResult)

    # ------------------------------------------------------------------
    # Test: decide_pipeline() not called for empty list
    # ------------------------------------------------------------------

    def test_decide_pipeline_not_called_when_no_events(self):
        """KROK 2C Test 2: decide_pipeline() not called for empty list."""
        ohlcv_data = self._setup_ohlcv()
        self.mock_price_detector.detect.return_value = []
        self.mock_volume_detector.detect.return_value = []

        engine = self._make_master_engine()
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        self.mock_ai_engine.decide_pipeline.assert_not_called()
        self.assertIsInstance(result, FinalAnalysisResult)

    # ------------------------------------------------------------------
    # Test: News runs when run_news=True
    # ------------------------------------------------------------------

    def test_news_runs_when_run_news_true(self):
        """KROK 2C Test 3: News runs when run_news=True."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=True, run_tavily=False, run_ai=False,
            reason="Test — run_news=True",
        )

        engine = self._make_master_engine()
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        self.mock_news_engine.process.assert_called_once()
        self.assertIsInstance(result, FinalAnalysisResult)

    # ------------------------------------------------------------------
    # Test: News does NOT run when run_news=False
    # ------------------------------------------------------------------

    def test_news_skipped_when_run_news_false(self):
        """KROK 2C Test 4: News skipped when run_news=False."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=False, run_ai=False,
            reason="Test — run_news=False",
        )

        engine = self._make_master_engine()
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        self.mock_news_engine.process.assert_not_called()
        self.assertIsInstance(result, FinalAnalysisResult)

    # ------------------------------------------------------------------
    # Test: AI runs when run_ai=True
    # ------------------------------------------------------------------

    def test_ai_runs_when_run_ai_true(self):
        """KROK 2C Test 5: AI runs when run_ai=True."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=False, run_ai=True,
            reason="Test — run_ai=True",
        )

        engine = self._make_master_engine()
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # process_event should be called for the event with run_ai=True
        self.mock_ai_engine.process_event.assert_called_once()
        self.assertIsInstance(result, FinalAnalysisResult)

    # ------------------------------------------------------------------
    # Test: AI does NOT run when run_ai=False
    # ------------------------------------------------------------------

    def test_ai_skipped_when_run_ai_false(self):
        """KROK 2C Test 6: AI skipped when run_ai=False."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=False, run_ai=False,
            reason="Test — run_ai=False",
        )

        engine = self._make_master_engine()
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # process_event must NOT be called when run_ai=False
        self.mock_ai_engine.process_event.assert_not_called()
        # Fallback process_data should still be called
        self.mock_ai_engine.process_data.assert_called_once()
        self.assertIsInstance(result, FinalAnalysisResult)


    # ------------------------------------------------------------------
    # Tests: Tavily Integration (KROK 3H)
    # ------------------------------------------------------------------


class TestMasterEngineTavilyIntegration(unittest.TestCase):
    """Integration tests for TavilyEventAdapter in the pipeline (KROK 3H)."""

    def setUp(self):
        self.mock_technical_engine = Mock()
        self.mock_news_engine = Mock()
        self.mock_ai_engine = Mock()
        self.mock_ranking_engine = Mock()
        self.mock_risk_engine = Mock()
        self.mock_hunter_engine = Mock()
        self.mock_analyst_engine = Mock()
        self.mock_price_detector = Mock()
        self.mock_volume_detector = Mock()
        self.mock_composer_engine = Mock()
        self.mock_quality_engine = Mock()
        self.mock_tavily_adapter = Mock()

        # Default: detectors return nothing
        self.mock_price_detector.detect.return_value = []
        self.mock_volume_detector.detect.return_value = []

        # Mock composer — pass-through
        self.mock_composer_engine.compose.side_effect = lambda events: events
        # Mock quality — pass-through
        self.mock_quality_engine.assess.side_effect = lambda ev: ev

        self.news_item = NewsItem(
            title="Test News", source="Test Source",
            publish_date=datetime.fromisoformat("2023-01-01"),
            url="http://example.com", summary="Test Content", sentiment=0.5,
        )
        self.mock_news_engine.process.return_value = [self.news_item]
        self.mock_ai_engine.process_data.return_value = AISignal(
            signal_type="BUY", confidence=0.9,
            generated_at=datetime.now(), reasoning="Test",
        )

    def _make_master_engine(self, tavily_adapter=None):
        return MasterEngine(
            technical_engine=self.mock_technical_engine,
            news_engine=self.mock_news_engine,
            ai_engine=self.mock_ai_engine,
            ranking_engine=self.mock_ranking_engine,
            risk_engine=self.mock_risk_engine,
            hunter_engine=self.mock_hunter_engine,
            analyst_engine=self.mock_analyst_engine,
            price_detector=self.mock_price_detector,
            volume_detector=self.mock_volume_detector,
            composer_engine=self.mock_composer_engine,
            quality_engine=self.mock_quality_engine,
            tavily_adapter=tavily_adapter,
        )

    def _make_mock_event(self, event_id="ev-0", ticker="TEST",
                         event_family=EventFamily.PRICE):
        ev = MagicMock(spec=MarketEvent)
        ev.ticker = ticker
        ev.timestamp_utc = datetime(2026, 7, 28, 12, 0, 0)
        ev.event_id = event_id
        ev.event_family = event_family
        ev.priority_raw = PriorityLevel.HIGH
        ev.confidence_level = 0.8
        ev.market = "NYSE"
        ev.instrument_type = InstrumentType.STOCK_USA
        ev.event_type = "PRICE_SURGE"
        ev.is_composite = False
        ev.composite_events = []
        ev.event_category = "Cenowe"
        ev.event_subcategory = None
        ev.tavily_context = None
        return ev

    def _setup_ohlcv(self):
        ohlcv_data = [
            MarketData(open=100.0, high=105.0, low=95.0, close=102.0,
                       volume=1000000, timestamp=1),
        ]
        class TechnicalResultWithData:
            def __init__(self, data):
                self.market_data = data
        self.mock_technical_engine.analyze.return_value = (
            TechnicalResultWithData(ohlcv_data))
        return ohlcv_data

    # ------------------------------------------------------------------
    # Test: run_tavily=False does NOT call adapter
    # ------------------------------------------------------------------

    def test_tavily_not_called_when_run_tavily_false(self):
        """Tavily adapter not called when run_tavily=False."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=False, run_ai=False,
            reason="Test — run_tavily=False",
        )

        engine = self._make_master_engine(tavily_adapter=self.mock_tavily_adapter)
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        self.mock_tavily_adapter.search_for_event.assert_not_called()
        self.assertIsNone(mock_event.tavily_context)
        self.assertIsInstance(result, FinalAnalysisResult)

    # ------------------------------------------------------------------
    # Test: run_tavily=True calls adapter exactly once
    # ------------------------------------------------------------------

    def test_tavily_called_when_run_tavily_true(self):
        """Tavily adapter called once when run_tavily=True."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=True, run_ai=False,
            reason="Test — run_tavily=True",
        )
        # Mock adapter to return a simple context
        from data.tavily.models import TavilyContext
        mock_ctx = TavilyContext("test query", 1, top_results=tuple(), sentiment=None)
        self.mock_tavily_adapter.search_for_event.return_value = mock_ctx

        engine = self._make_master_engine(tavily_adapter=self.mock_tavily_adapter)
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        self.mock_tavily_adapter.search_for_event.assert_called_once()
        self.assertIsNotNone(mock_event.tavily_context)
        self.assertIsInstance(mock_event.tavily_context, dict)
        self.assertEqual(mock_event.tavily_context["query"], "test query")
        self.assertIsInstance(result, FinalAnalysisResult)

    # ------------------------------------------------------------------
    # Test: adapter receives exactly the MarketEvent
    # ------------------------------------------------------------------

    def test_adapter_receives_market_event(self):
        """Tavily adapter receives the exact MarketEvent."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=True, run_ai=False,
            reason="Test — run_tavily=True",
        )
        from data.tavily.models import TavilyContext
        mock_ctx = TavilyContext("q", 0)
        self.mock_tavily_adapter.search_for_event.return_value = mock_ctx

        engine = self._make_master_engine(tavily_adapter=self.mock_tavily_adapter)
        events_out = []
        engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        call_args = self.mock_tavily_adapter.search_for_event.call_args[0]
        self.assertIs(call_args[0], mock_event)

    # ------------------------------------------------------------------
    # Test: no adapter — run_tavily=False still works
    # ------------------------------------------------------------------

    def test_no_adapter_run_tavily_false_works(self):
        """Pipeline works fine without adapter when run_tavily=False."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=False, run_ai=False,
            reason="Test",
        )

        engine = self._make_master_engine(tavily_adapter=None)
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        self.assertIsInstance(result, FinalAnalysisResult)

    # ------------------------------------------------------------------
    # Test: no adapter — run_tavily=True skips with log
    # ------------------------------------------------------------------

    def test_no_adapter_run_tavily_true_skips(self):
        """Pipeline continues without error when adapter missing but run_tavily=True."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=True, run_ai=False,
            reason="Test — run_tavily=True but no adapter",
        )

        engine = self._make_master_engine(tavily_adapter=None)
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # Pipeline should complete without exception
        self.assertIsInstance(result, FinalAnalysisResult)
        # tavily_context should remain None
        self.assertIsNone(mock_event.tavily_context)

    # ------------------------------------------------------------------
    # Test: Tavily exception is caught and pipeline continues
    # ------------------------------------------------------------------

    def test_tavily_exception_caught_pipeline_continues(self):
        """When Tavily fails, pipeline continues and returns result."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=True, run_ai=False,
            reason="Test",
        )
        self.mock_tavily_adapter.search_for_event.side_effect = (
            TavilyTimeoutError("timeout")
        )

        engine = self._make_master_engine(tavily_adapter=self.mock_tavily_adapter)
        events_out = []
        result = engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # Pipeline must complete
        self.assertIsInstance(result, FinalAnalysisResult)
        # tavily_context should remain None after failure
        self.assertIsNone(mock_event.tavily_context)

    # ------------------------------------------------------------------
    # Test: run_news unchanged by Tavily integration
    # ------------------------------------------------------------------

    def test_run_news_still_works(self):
        """run_news behavior is unchanged when Tavily is present."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=True, run_tavily=True, run_ai=False,
            reason="Test",
        )
        from data.tavily.models import TavilyContext
        self.mock_tavily_adapter.search_for_event.return_value = TavilyContext("q", 0)

        engine = self._make_master_engine(tavily_adapter=self.mock_tavily_adapter)
        events_out = []
        engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # News must still be called
        self.mock_news_engine.process.assert_called_once()

    # ------------------------------------------------------------------
    # Test: run_ai unchanged by Tavily integration
    # ------------------------------------------------------------------

    def test_run_ai_still_works(self):
        """run_ai behavior is unchanged when Tavily is present."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=True, run_ai=True,
            reason="Test",
        )
        from data.tavily.models import TavilyContext
        self.mock_tavily_adapter.search_for_event.return_value = TavilyContext("q", 0)

        engine = self._make_master_engine(tavily_adapter=self.mock_tavily_adapter)
        events_out = []
        engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # process_event must be called for AI
        self.mock_ai_engine.process_event.assert_called_once()

    # ------------------------------------------------------------------
    # Test: TavilyContext stored as dict on event
    # ------------------------------------------------------------------

    def test_tavily_context_stored_as_dict(self):
        """TavilyContext is stored as a dict on MarketEvent.tavily_context."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=True, run_ai=False,
            reason="Test",
        )
        from data.tavily.models import TavilyContext, TavilyResultItem
        item = TavilyResultItem(
            title="Test", url="https://test.com", content="Test content",
            score=0.95,
            published_date=datetime(2026, 7, 28, 10, 0, 0,
                                    tzinfo=__import__("datetime").timezone.utc),
        )
        mock_ctx = TavilyContext(
            query="stock TEST NYSE PRICE_SURGE recent news analysis why",
            results_count=1,
            top_results=(item,),
            sentiment=0.5,
        )
        self.mock_tavily_adapter.search_for_event.return_value = mock_ctx

        engine = self._make_master_engine(tavily_adapter=self.mock_tavily_adapter)
        events_out = []
        engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        ctx = mock_event.tavily_context
        assert isinstance(ctx, dict)
        assert ctx["query"] == "stock TEST NYSE PRICE_SURGE recent news analysis why"
        assert ctx["results_count"] == 1
        assert len(ctx["top_results"]) == 1
        assert ctx["top_results"][0]["title"] == "Test"
        assert ctx["top_results"][0]["score"] == 0.95
        assert ctx["sentiment"] == 0.5

    # ------------------------------------------------------------------
    # Test: Default constructor preserves backward compatibility
    # ------------------------------------------------------------------

    def test_default_tavily_adapter_is_none(self):
        """MasterEngine without tavily_adapter sets it to None."""
        engine = self._make_master_engine(tavily_adapter=None)
        self.assertIsNone(engine._tavily_adapter)

    # ------------------------------------------------------------------
    # Tests: Tavily → AI enrichment (KROK 4A)
    # ------------------------------------------------------------------

    def test_tavily_context_available_in_ai_context(self):
        """When both run_tavily=True and run_ai=True, tavily_context
        is included in ai_context."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=True, run_ai=True,
            reason="Test — Tavily + AI",
        )
        from data.tavily.models import TavilyContext
        mock_ctx = TavilyContext("search query tavily", 2, top_results=tuple(),
                                sentiment=None)
        self.mock_tavily_adapter.search_for_event.return_value = mock_ctx

        engine = self._make_master_engine(tavily_adapter=self.mock_tavily_adapter)
        events_out = []
        engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # ai_context must contain tavily_context key
        self.assertIsNotNone(mock_event.ai_context)
        self.assertIn("tavily_context", mock_event.ai_context)
        self.assertEqual(
            mock_event.ai_context["tavily_context"]["query"],
            "search query tavily",
        )

    def test_ai_context_without_tavily_when_run_tavily_false(self):
        """When run_tavily=False, ai_context does NOT contain tavily_context."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=False, run_ai=True,
            reason="Test — AI only",
        )

        engine = self._make_master_engine(tavily_adapter=self.mock_tavily_adapter)
        events_out = []
        engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        self.assertNotIn("tavily_context", mock_event.ai_context)

    def test_tavily_run_before_ai(self):
        """Tavily adapter is called before DecisionEngine.process_event for AI."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=True, run_ai=True,
            reason="Test — Tavily + AI",
        )
        from data.tavily.models import TavilyContext
        self.mock_tavily_adapter.search_for_event.return_value = TavilyContext("q", 0)

        # Track call order
        call_order = []
        self.mock_tavily_adapter.search_for_event = Mock(
            side_effect=lambda *a, **kw: call_order.append("tavily")
            or TavilyContext("q", 0),
        )
        self.mock_ai_engine.process_event = Mock(
            side_effect=lambda *a, **kw: call_order.append("ai")
            or AISignal(signal_type="BUY", confidence=0.9,
                        generated_at=datetime.now(), reasoning="Test"),
        )

        engine = self._make_master_engine(tavily_adapter=self.mock_tavily_adapter)
        events_out = []
        engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        # Tavily must be called before AI
        self.assertEqual(call_order, ["tavily", "ai"])

    def test_tavily_context_not_in_ai_when_no_tavily_context(self):
        """When tavily_context is None (no Tavily run or failed), ai_context
        does NOT get a tavily_context key."""
        ohlcv_data = self._setup_ohlcv()
        mock_event = self._make_mock_event("ev-0")
        # Ensure tavily_context is None
        mock_event.tavily_context = None
        self.mock_price_detector.detect.return_value = [mock_event]

        self.mock_ai_engine.decide_pipeline.return_value = PipelineDecision(
            run_news=False, run_tavily=False, run_ai=True,
            reason="Test — AI only, no Tavily",
        )

        engine = self._make_master_engine()
        events_out = []
        engine.run_analysis(
            "TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out, ohlcv_data=ohlcv_data,
        )

        self.assertNotIn("tavily_context", mock_event.ai_context)


# ------------------------------------------------------------------
# TavilyTimeoutError used in test — import at module level for tests
# ------------------------------------------------------------------

from data.tavily.errors import TavilyTimeoutError


if __name__ == "__main__":
    unittest.main()
