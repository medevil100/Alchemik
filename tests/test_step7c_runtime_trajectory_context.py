"""Test-first RED — trajektoria 1h w kontekście RuntimeService i MarketEvent."""
from __future__ import annotations

from datetime import datetime, timezone

from application.runtime import RuntimeService
from application.sqlite_history_repository import SQLiteHistoryRepository
from data.models.instrument_observation import InstrumentObservation
from data.models.instrument_reading import InstrumentReading
from data.models.market_data import MarketData


def _market(ts, candle_state, close, timeframe="1h"):
    return MarketData(
        timestamp=ts,
        open=100.0,
        high=110.0,
        low=90.0,
        close=close,
        volume=1000.0,
        timeframe=timeframe,
        candle_state=candle_state,
    )


class TestRuntimeTrajectoryContext:
    def _make_runtime(self, tmp_path):
        repo = SQLiteHistoryRepository(tmp_path / "rt.db")
        runtime = RuntimeService(
            hunter_engine=None,
            master_engine=None,
            history_repository=repo,
        )
        return repo, runtime

    def _seed(self, repo, runtime):
        anchor_ts = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        cur_ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)

        # Kolizyjny 5m — musi zostać wykluczony.
        obs5m = InstrumentObservation(
            observation_id="obs-5m", instrument_id="AAA", timeframe="5m",
        )
        repo.save_reading(obs5m, InstrumentReading(
            reading_id="r-5m", observation_id="obs-5m", instrument_id="AAA",
            market_data_timestamp=cur_ts, scan_timestamp=cur_ts,
            open=99.0, high=99.0, low=99.0, close=99.0, volume=1.0,
            timeframe="5m", candle_state="LEGACY_UNKNOWN",
        ))

        runtime._persist_observation_and_reading_full(
            "AAA", [_market(anchor_ts, "CLOSED", 100.0)]
        )
        runtime._persist_observation_and_reading_full("AAA", [_market(cur_ts, "OPEN", 101.0)])
        runtime._persist_observation_and_reading_full("AAA", [_market(cur_ts, "OPEN", 102.0)])
        runtime._persist_observation_and_reading_full("AAA", [_market(cur_ts, "OPEN", 103.0)])
        runtime._persist_observation_and_reading_full("AAA", [_market(cur_ts, "CLOSED", 104.0)])
        return anchor_ts, cur_ts

    def test_candle_trajectory_1h_structure_and_deltas(self, tmp_path):
        repo, runtime = self._make_runtime(tmp_path)
        anchor_ts, cur_ts = self._seed(repo, runtime)

        previous_closed = repo.get_previous_closed("AAA", "1h", cur_ts)
        trajectory = repo.get_current_trajectory("AAA", "1h", cur_ts)

        assert previous_closed is not None
        assert previous_closed.candle_state == "CLOSED"
        assert previous_closed.market_data_timestamp == anchor_ts
        assert [r.revision_number for r in trajectory] == [1, 2, 3, 4]
        assert [r.candle_state for r in trajectory] == ["OPEN", "OPEN", "OPEN", "CLOSED"]

        context = runtime._build_candle_trajectory_1h("AAA", cur_ts)

        assert context["timeframe"] == "1h"
        assert context["instrument_id"] == "AAA"
        assert context["candle_start"] == cur_ts.isoformat()
        assert context["previous_closed"]["reading_id"] == previous_closed.reading_id
        assert context["previous_closed"]["candle_state"] == "CLOSED"
        assert context["previous_closed_close"] == 100.0

        states = context["states"]
        assert [s["revision_number"] for s in states] == [1, 2, 3, 4]
        assert [s["candle_state"] for s in states] == ["OPEN", "OPEN", "OPEN", "CLOSED"]

        s0, s1, s2, s3 = states
        # Pierwszy stan: brak poprzedniego stanu tej samej świecy.
        assert s0["previous_state_close"] is None
        assert s0["close_delta_vs_previous_state"] is None
        # Kolejne stany porównywane z bezpośrednio poprzednią wersją.
        assert s1["previous_state_close"] == 101.0
        assert s1["close_delta_vs_previous_state"] == 1.0
        assert s2["previous_state_close"] == 102.0
        assert s2["close_delta_vs_previous_state"] == 1.0
        assert s3["previous_state_close"] == 103.0
        assert s3["close_delta_vs_previous_state"] == 1.0
        # Wszystkie porównywane ze stałym previous_closed_close=100.
        assert [s["previous_closed_close"] for s in states] == [100.0] * 4
        assert [s["close_delta_vs_previous_closed"] for s in states] == [1.0, 2.0, 3.0, 4.0]
        # Kolizyjny 5m nie jest częścią trajektorii ani previous_closed.
        assert all(s["timeframe"] == "1h" for s in states)
        assert previous_closed.timeframe == "1h"

    def test_candle_progress_accepted_flows_to_runtime(self, tmp_path):
        repo, runtime = self._make_runtime(tmp_path)

        cur_ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        r1 = runtime._persist_observation_and_reading_full("AAA", [_market(cur_ts, "OPEN", 101.0)])
        r2 = runtime._persist_observation_and_reading_full("AAA", [_market(cur_ts, "OPEN", 102.0)])
        r3 = runtime._persist_observation_and_reading_full("AAA", [_market(cur_ts, "CLOSED", 103.0)])

        assert r1[0] == "ACCEPTED"
        assert r2[0] == "CANDLE_PROGRESS_ACCEPTED"
        assert r3[0] == "CANDLE_PROGRESS_ACCEPTED"

        trajectory = repo.get_current_trajectory("AAA", "1h", cur_ts)
        assert [r.revision_number for r in trajectory] == [1, 2, 3]
        assert [r.candle_state for r in trajectory] == ["OPEN", "OPEN", "CLOSED"]

    def test_attach_preserves_existing_ai_context(self, tmp_path):
        repo, runtime = self._make_runtime(tmp_path)
        anchor_ts, cur_ts = self._seed(repo, runtime)

        from data.models.event_enums import (
            EventFamily, EventOwner, InstrumentType, PriorityLevel, SignalTiming,
        )
        from data.models.market_event import MarketEvent

        event = MarketEvent(
            event_id="evt-trajectory",
            timestamp_utc=datetime.now(timezone.utc),
            ticker="AAA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            event_family=EventFamily.SYSTEM,
            event_category="System",
            event_type="TRAJECTORY_TEST",
            signal_timing=SignalTiming.LEADING,
            priority_raw=PriorityLevel.HIGH,
            priority_final=PriorityLevel.HIGH,
            confidence_level=0.8,
            detection_source="test",
            event_owner=EventOwner.TechnicalEngine,
            ai_context={"existing_key": "preserved", "tavily_context": {"q": "news"}},
        )

        context = runtime._build_candle_trajectory_1h("AAA", cur_ts)
        runtime._attach_candle_trajectory_to_event(event, context)

        assert event.ai_context["existing_key"] == "preserved"
        assert event.ai_context["tavily_context"] == {"q": "news"}
        assert "candle_trajectory_1h" in event.ai_context
        assert len([k for k in event.ai_context if k == "candle_trajectory_1h"]) == 1
        assert event.ai_context["candle_trajectory_1h"]["candle_start"] == cur_ts.isoformat()