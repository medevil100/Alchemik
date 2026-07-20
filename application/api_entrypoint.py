"""
Minimal read-only HTTP API for ALCHEMIK runtime data.

This is a separate process from RuntimeService. It provides read-only access
to stored cycles and MarketEvents via a RESTful HTTP API.

Usage:
    python -m application.api_entrypoint

Default address: http://localhost:8000
Override DB path: ALCHEMIK_DB_PATH environment variable
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse

from application.read_service import RuntimeReadService

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Application setup
# ------------------------------------------------------------------

description = """
ALCHEMIK Runtime Read API

A read-only HTTP API for querying stored runtime data (cycles and MarketEvents).
This API is independent of RuntimeService and can run as a separate process.

**Important**: This API is READ-ONLY. It does not start engines, generate events,
or modify the database.
"""

app = FastAPI(
    title="ALCHEMIK Runtime API",
    description=description,
    version="1.0.0",
    # No docs in production? Keep them for development convenience.
)

# ------------------------------------------------------------------
# Dependency: read service
# ------------------------------------------------------------------

def _get_db_path() -> Optional[Path]:
    """Get database path from environment variable or use default."""
    env_path = os.environ.get("ALCHEMIK_DB_PATH")
    if env_path:
        return Path(env_path)
    return None


def get_read_service() -> RuntimeReadService:
    """Create or get the RuntimeReadService instance."""
    # FastAPI lifespan could handle this, but for simplicity:
    global _read_service
    if _read_service is None:
        _read_service = RuntimeReadService(db_path=_get_db_path())
    return _read_service


_read_service: Optional[RuntimeReadService] = None

# ------------------------------------------------------------------
# Pagination helpers
# ------------------------------------------------------------------

def _validate_pagination(limit: int, offset: int) -> None:
    """Validate pagination parameters, raise 400 on invalid values."""
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")


def _validate_date(date_str: Optional[str]) -> Optional[str]:
    """Validate an ISO 8601 date string. Returns normalized string or None."""
    if date_str is None:
        return None
    try:
        # Validate it's a proper ISO datetime
        parsed = datetime.fromisoformat(date_str)
        return parsed.isoformat()
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: '{date_str}'. Use ISO 8601 (e.g., '2026-07-20T12:00:00').",
        )


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint.

    Returns API status, database availability, journal mode, and schema version.
    """
    service = get_read_service()
    health_info = service.get_storage_health()

    if health_info.get("status") == "error":
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "api": "running",
                "database": "unavailable",
            },
        )

    return {
        "status": "ok",
        "api": "running",
        "database": "available",
        "journal_mode": health_info.get("journal_mode"),
        "schema_version": health_info.get("schema_version"),
        "cycle_count": health_info.get("cycle_count"),
        "event_count": health_info.get("event_count"),
    }


@app.get("/api/v1/runtime/statistics")
async def runtime_statistics():
    """Return runtime statistics: cycle count, event count, latest cycle info."""
    service = get_read_service()
    stats = service.get_runtime_statistics()
    return stats


@app.get("/api/v1/cycles")
async def list_cycles(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of cycles"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
):
    """List recent cycles (without full report JSON)."""
    service = get_read_service()
    return service.get_latest_cycles(limit=limit, offset=offset)


@app.get("/api/v1/cycles/{cycle_id}")
async def get_cycle(cycle_id: str):
    """Get a single cycle by its ID."""
    service = get_read_service()
    cycle = service.get_cycle(cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"Cycle '{cycle_id}' not found")
    return cycle


@app.get("/api/v1/market-events")
async def list_market_events(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of events"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    ticker: Optional[str] = Query(None, description="Filter by ticker (exact match)"),
    market: Optional[str] = Query(None, description="Filter by market (exact match)"),
    instrument_type: Optional[str] = Query(None, description="Filter by instrument type"),
    event_family: Optional[str] = Query(None, description="Filter by event family"),
    event_type: Optional[str] = Query(None, description="Filter by event type (exact match)"),
    priority_final: Optional[str] = Query(None, description="Filter by final priority"),
    date_from: Optional[str] = Query(None, description="Filter: created_at >= this ISO datetime"),
    date_to: Optional[str] = Query(None, description="Filter: created_at <= this ISO datetime"),
):
    """List MarketEvents with optional filters.

    All filters are optional. At least one filter or pagination controls the result size.
    """
    # Validate dates
    _validate_date(date_from) if date_from else None
    _validate_date(date_to) if date_to else None

    service = get_read_service()
    return service.query_market_events(
        limit=limit,
        offset=offset,
        ticker=ticker,
        market=market,
        instrument_type=instrument_type,
        event_family=event_family,
        event_type=event_type,
        priority_final=priority_final,
        date_from=date_from,
        date_to=date_to,
    )


@app.get("/api/v1/market-events/{event_id}")
async def get_market_event(event_id: str):
    """Get a single MarketEvent by its event_id."""
    service = get_read_service()
    event = service.get_market_event_by_id(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"MarketEvent '{event_id}' not found")
    return event


@app.get("/api/v1/tickers/{ticker}/market-events")
async def get_ticker_market_events(
    ticker: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of events"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    date_from: Optional[str] = Query(None, description="Filter: created_at >= this ISO datetime"),
    date_to: Optional[str] = Query(None, description="Filter: created_at <= this ISO datetime"),
):
    """List MarketEvents for a specific ticker.

    Ticker is normalized to uppercase. The original symbol meaning is preserved.
    """
    # Normalize ticker
    normalized_ticker = ticker.upper()

    # Validate dates
    date_from = _validate_date(date_from) if date_from else None
    date_to = _validate_date(date_to) if date_to else None

    service = get_read_service()

    if date_from or date_to:
        # Use query with filters
        return service.query_market_events(
            limit=limit,
            offset=offset,
            ticker=normalized_ticker,
            date_from=date_from,
            date_to=date_to,
        )
    else:
        return service.get_market_events_by_ticker(
            ticker=normalized_ticker,
            limit=limit,
            offset=offset,
        )


# ------------------------------------------------------------------
# Error handlers
# ------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Standard HTTP error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Catch-all error handler - never expose internals."""
    logger.error("Unhandled error: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def main():
    """Run the API server with uvicorn."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Starting ALCHEMIK Runtime API server")
    logger.info("Default DB path: %s", _get_db_path() or "default (RuntimeConfig)")

    uvicorn.run(
        "application.api_entrypoint:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()