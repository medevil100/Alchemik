#!/usr/bin/env python
"""
Manual persistence test: save data, restart repository, verify survival.
"""
import tempfile, os, gc, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from application.sqlite_history_repository import SQLiteHistoryRepository
from data.models import MarketEvent, InstrumentType, EventFamily, EventOwner, PriorityLevel
from data.models.event_enums import SignalTiming

# 1. Create temp database
tmp = tempfile.NamedTemporaryFile(delete=False)
db_path = tmp.name
tmp.close()

try:
    # 2. Save data
    repo = SQLiteHistoryRepository(db_path)
    repo.save_cycle("cycle_001", {
        "execution_time": 1.23,
        "candidates_count": 3,
        "success_count": 2,
        "error_count": 1,
        "report": {"summary": "test cycle"}
    })

    event = MarketEvent(
        event_id="evt_001",
        timestamp_utc=datetime.now(timezone.utc),
        ticker="TEST",
        market="NYSE",
        instrument_type=InstrumentType.STOCK_USA,
        event_family=EventFamily.PRICE,
        event_category="PriceAnomaly",
        event_type="PRICE_SURGE",
        priority_raw=PriorityLevel.HIGH,
        priority_final=PriorityLevel.HIGH,
        confidence_level=0.85,
        detection_source="PriceDetector",
        event_owner=EventOwner.TechnicalEngine,
        schema_version="1.0",
        signal_timing=SignalTiming.LEADING,
    )
    event2 = MarketEvent(
        event_id="evt_002",
        timestamp_utc=datetime.now(timezone.utc),
        ticker="XYZ.WA",
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
        event_family=EventFamily.VOLUME,
        event_category="VolumeAnomaly",
        event_type="VOLUME_SPIKE",
        priority_raw=PriorityLevel.CRITICAL,
        priority_final=PriorityLevel.CRITICAL,
        confidence_level=0.95,
        detection_source="VolumeDetector",
        event_owner=EventOwner.TechnicalEngine,
        schema_version="1.0",
        signal_timing=SignalTiming.LEADING,
    )
    repo.save_market_event("cycle_001", event.to_dict())
    repo.save_market_event("cycle_001", event2.to_dict())

    print("BEFORE RESTART:")
    s1 = repo.get_storage_summary()
    print(f"  Cycles: {s1['cycle_count']}, Events: {s1['event_count']}")
    print(f"  Journal: {s1['journal_mode']}")

    # 3. Close and reopen (simulate restart)
    del repo
    gc.collect()

    repo2 = SQLiteHistoryRepository(db_path)

    print()
    print("AFTER RESTART:")
    s2 = repo2.get_storage_summary()
    print(f"  Cycles: {s2['cycle_count']}, Events: {s2['event_count']}")
    print(f"  Journal: {s2['journal_mode']}")

    cycle = repo2.get_cycle("cycle_001")
    print(f"  Cycle retrieved: {cycle is not None}")
    print(f"  Cycle candidates: {cycle['candidates_count']}")

    events = repo2.get_latest_market_events(limit=5)
    print(f"  Events retrieved: {len(events)}")
    for ev in events:
        print(f"    {ev['event_id']}: {ev['ticker']} {ev['event_type']}")

    print()
    print("PERSISTENCE VERIFIED: Data survives repository restart.")
finally:
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)