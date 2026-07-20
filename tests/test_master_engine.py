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
        result = self.master_engine.run_analysis(symbol)

        # Verify each dependency was called exactly once
        self.mock_technical_engine.analyze.assert_called_once_with([symbol])
        self.mock_news_engine.process.assert_called_once_with([symbol])
        self.mock_ai_engine.process_data.assert_called_once_with({"symbol": symbol, "technical": self.market_data, "news": [self.news_item]})
        self.mock_ranking_engine.calculate_ranking.assert_called_once_with([self.mock_ai_engine.process_data.return_value])
        self.mock_risk_engine.assess_risk.assert_called_once_with(self.mock_ai_engine.process_data.return_value, self.mock_ranking_engine.calculate_ranking.return_value)
        self.mock_hunter_engine.scan.assert_called_once_with([{"symbol": symbol, "risk": self.mock_risk_engine.assess_risk.return_value, "ranking": self.mock_ranking_engine.calculate_ranking.return_value}])
        self.mock_analyst_engine.generate_analysis.assert_called_once_with(self.mock_hunter_engine.scan.return_value)

        # Verify the result is a FinalAnalysisResult
        self.assertIsInstance(result, FinalAnalysisResult)

        # Detectors are not called in this test because the mock technical
        # result is a plain MarketData object (no market_data attribute).
        # Detector calling is tested separately in
        # test_run_analysis_detectors_called_with_technical_market_data.

    def test_invalid_symbol(self):
        with self.assertRaises(ValueError):
            self.master_engine.run_analysis("")
        with self.assertRaises(ValueError):
            self.master_engine.run_analysis(123)

    def test_error_handling(self):
        # Simulate an error in one of the engines
        self.mock_technical_engine.analyze.side_effect = Exception("Technical Engine Error")
        with self.assertRaises(Exception) as context:
            self.master_engine.run_analysis("TEST")
        self.assertIn("Technical Engine Error", str(context.exception))

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

    def test_run_analysis_detectors_called_with_technical_market_data(self):
        """Test that run_analysis calls detectors with market_data from technical result."""
        # Technical result has market_data attribute
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = [
                    MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
                    MarketData(open=102.0, high=108.0, low=101.0, close=107.0, volume=2000000, timestamp=2),
                ]

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        result = self.master_engine.run_analysis("TEST")

        # Verify detectors were called
        self.mock_price_detector.detect.assert_called_once()
        self.mock_volume_detector.detect.assert_called_once()

        # Verify the old pipeline still works
        self.mock_news_engine.process.assert_called_once()
        self.mock_ai_engine.process_data.assert_called_once()
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_run_analysis_pipeline_unchanged(self):
        """Test that the existing pipeline (AnalysisResult, AISignal, FinalAnalysisResult) is unchanged."""
        # Technical result without market_data (no detectors triggered)
        class TechnicalResultWithoutData:
            def __init__(self):
                self.market_data = None

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithoutData()
        result = self.master_engine.run_analysis("TEST")

        # Verify old pipeline still works
        self.mock_news_engine.process.assert_called_once()
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
    # NEW TESTS: Market and instrument_type propagation
    # ------------------------------------------------------------------

    def test_run_analysis_passes_market_to_detectors(self):
        """Test that market is passed correctly to detectors through run_analysis."""
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = [
                    MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
                ]

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        self.master_engine.run_analysis("TEST", market="GPW", instrument_type=InstrumentType.STOCK_GPW)

        # Verify both detectors received the correct market
        self.mock_price_detector.detect.assert_called_once()
        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["market"], "GPW")

        self.mock_volume_detector.detect.assert_called_once()
        volume_kwargs = self.mock_volume_detector.detect.call_args.kwargs
        self.assertEqual(volume_kwargs["market"], "GPW")

    def test_run_analysis_passes_instrument_type_to_detectors(self):
        """Test that instrument_type is passed correctly to detectors through run_analysis."""
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = [
                    MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
                ]

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        self.master_engine.run_analysis("TEST", market="GPW", instrument_type=InstrumentType.STOCK_GPW)

        # Verify both detectors received the correct instrument_type
        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["instrument_type"], InstrumentType.STOCK_GPW)

        volume_kwargs = self.mock_volume_detector.detect.call_args.kwargs
        self.assertEqual(volume_kwargs["instrument_type"], InstrumentType.STOCK_GPW)

    def test_usa_instrument_passes_correct_values(self):
        """Test that USA instrument passes NYSE and STOCK_USA."""
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = [
                    MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
                ]

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        self.master_engine.run_analysis("TEST", market="NYSE", instrument_type=InstrumentType.STOCK_USA)

        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["market"], "NYSE")
        self.assertEqual(price_kwargs["instrument_type"], InstrumentType.STOCK_USA)

        volume_kwargs = self.mock_volume_detector.detect.call_args.kwargs
        self.assertEqual(volume_kwargs["market"], "NYSE")
        self.assertEqual(volume_kwargs["instrument_type"], InstrumentType.STOCK_USA)

    def test_gpw_instrument_passes_correct_values(self):
        """Test that GPW instrument passes GPW and STOCK_GPW."""
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = [
                    MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
                ]

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        self.master_engine.run_analysis("XYZ.WA", market="GPW", instrument_type=InstrumentType.STOCK_GPW)

        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["market"], "GPW")
        self.assertEqual(price_kwargs["instrument_type"], InstrumentType.STOCK_GPW)

        volume_kwargs = self.mock_volume_detector.detect.call_args.kwargs
        self.assertEqual(volume_kwargs["market"], "GPW")
        self.assertEqual(volume_kwargs["instrument_type"], InstrumentType.STOCK_GPW)

    def test_no_hardcoded_nyse(self):
        """Test that run_analysis does NOT default to NYSE."""
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = [
                    MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
                ]

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        # Call with NASDAQ to verify no NYSE default
        self.master_engine.run_analysis("TEST", market="NASDAQ", instrument_type=InstrumentType.STOCK_USA)

        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["market"], "NASDAQ")
        self.assertNotEqual(price_kwargs["market"], "NYSE")

    def test_no_hardcoded_stock_usa(self):
        """Test that run_analysis does NOT default to STOCK_USA."""
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = [
                    MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
                ]

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()
        # Call with STOCK_GPW to verify no STOCK_USA default
        self.master_engine.run_analysis("TEST", market="GPW", instrument_type=InstrumentType.STOCK_GPW)

        price_kwargs = self.mock_price_detector.detect.call_args.kwargs
        self.assertEqual(price_kwargs["instrument_type"], InstrumentType.STOCK_GPW)
        self.assertNotEqual(price_kwargs["instrument_type"], InstrumentType.STOCK_USA)

    def test_events_out_receives_detected_events(self):
        """Test that events_out parameter collects MarketEvents from detectors."""
        class TechnicalResultWithData:
            def __init__(self):
                self.market_data = [
                    MarketData(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1),
                ]

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithData()

        mock_price_event = MagicMock(spec=MarketEvent)
        mock_volume_event = MagicMock(spec=MarketEvent)
        self.mock_price_detector.detect.return_value = [mock_price_event]
        self.mock_volume_detector.detect.return_value = [mock_volume_event]

        events_out = []
        result = self.master_engine.run_analysis(
            "TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out,
        )

        self.assertEqual(len(events_out), 2)
        self.assertIn(mock_price_event, events_out)
        self.assertIn(mock_volume_event, events_out)
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_events_out_empty_when_no_market_data(self):
        """Test that events_out remains empty when no market_data is available."""
        class TechnicalResultWithoutData:
            def __init__(self):
                self.market_data = None

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithoutData()

        events_out = []
        result = self.master_engine.run_analysis(
            "TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            events_out=events_out,
        )

        self.assertEqual(len(events_out), 0)
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_old_pipeline_unchanged_with_new_params(self):
        """Test that old pipeline is unchanged when new params (market, instrument_type) are used."""
        class TechnicalResultWithoutData:
            def __init__(self):
                self.market_data = None

        self.mock_technical_engine.analyze.return_value = TechnicalResultWithoutData()

        result = self.master_engine.run_analysis(
            "TEST",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
        )

        # Old pipeline still works
        self.mock_news_engine.process.assert_called_once()
        self.mock_ai_engine.process_data.assert_called_once()
        self.mock_ranking_engine.calculate_ranking.assert_called_once()
        self.mock_risk_engine.assess_risk.assert_called_once()
        self.mock_hunter_engine.scan.assert_called_once()
        self.mock_analyst_engine.generate_analysis.assert_called_once()
        self.assertIsInstance(result, FinalAnalysisResult)

if __name__ == "__main__":
    unittest.main()