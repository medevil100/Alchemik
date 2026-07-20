# ALCHEMIK Runtime Read API

## Overview

The ALCHEMIK Runtime Read API provides read-only HTTP access to stored runtime data (cycles and MarketEvents). It is a **separate process** from RuntimeService—both can run independently using the same SQLite database.

**Architecture**: `RuntimeService → SQLite → RuntimeReadService → FastAPI → HTTP`

## Tech Stack

- **Framework**: FastAPI (async Python web framework)
- **Server**: Uvicorn (ASGI server)
- **Storage**: SQLite with WAL mode (same database as RuntimeService)

## Running the API

```bash
# From the project root:
python -m application.api_entrypoint
```

Default address: `http://localhost:8000`

### Custom Database Path

Set the `ALCHEMIK_DB_PATH` environment variable to point to a different SQLite database:

```bash
# Windows (PowerShell):
$env:ALCHEMIK_DB_PATH="C:\path\to\test.db"
python -m application.api_entrypoint

# Windows (CMD):
set ALCHEMIK_DB_PATH=C:\path\to\test.db
python -m application.api_entrypoint

# Linux/Mac:
ALCHEMIK_DB_PATH=/path/to/test.db python -m application.api_entrypoint
```

If not set, the API uses the default path from `RuntimeConfig.get_db_path()` (`data/runtime/alchemik_runtime.db`).

## API Endpoints

### Health Check

**`GET /health`**

Returns API status and database metadata.

```json
{
  "status": "ok",
  "api": "running",
  "database": "available",
  "journal_mode": "wal",
  "schema_version": 1,
  "cycle_count": 42,
  "event_count": 156
}
```

### Runtime Statistics

**`GET /api/v1/runtime/statistics`**

Returns cycle count, event count, latest cycle info, and storage metadata.

```json
{
  "cycle_count": 42,
  "event_count": 156,
  "latest_cycle": {
    "cycle_id": "1721490000.0",
    "execution_time": 12.5,
    "candidates_count": 15,
    "success_count": 12,
    "error_count": 0,
    "status": "completed",
    "error_message": null,
    "created_at": "2026-07-20T12:00:00"
  },
  "storage": {
    "journal_mode": "wal",
    "schema_version": 1
  }
}
```

### List Cycles

**`GET /api/v1/cycles`**

Returns recent cycle summaries (without full report JSON).

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | int | 50 | 200 | Maximum number of cycles |
| `offset` | int | 0 | - | Number of records to skip |

```json
{
  "items": [
    {
      "cycle_id": "1721490000.0",
      "execution_time": 12.5,
      "candidates_count": 15,
      "success_count": 12,
      "error_count": 0,
      "status": "completed",
      "error_message": null,
      "created_at": "2026-07-20T12:00:00"
    }
  ],
  "limit": 50,
  "offset": 0,
  "returned": 1
}
```

### Get Single Cycle

**`GET /api/v1/cycles/{cycle_id}`**

Returns a complete cycle with full report JSON.

- 200: Cycle found
- 404: Cycle not found

### List MarketEvents

**`GET /api/v1/market-events`**

Returns MarketEvents with optional filtering. All filters are optional.

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Max events (default: 50, max: 200) |
| `offset` | int | Records to skip (default: 0) |
| `ticker` | str | Filter by ticker (exact match) |
| `market` | str | Filter by market (exact match) |
| `instrument_type` | str | Filter by instrument type |
| `event_family` | str | Filter by event family |
| `event_type` | str | Filter by event type (exact match) |
| `priority_final` | str | Filter by final priority |
| `date_from` | str | ISO 8601 datetime (created_at >=) |
| `date_to` | str | ISO 8601 datetime (created_at <=) |

```json
{
  "items": [
    {
      "event_id": "a1b2c3d4-...",
      "timestamp_utc": "2026-07-20T12:00:00+00:00",
      "ticker": "XYZ.WA",
      "market": "GPW",
      "instrument_type": "STOCK_GPW",
      "event_family": "PRICE",
      "event_category": "Cenowe",
      "event_type": "PRICE_SURGE",
      "priority_raw": "HIGH",
      "priority_final": "CRITICAL",
      "confidence_level": 0.85,
      "...": "..."
    }
  ],
  "limit": 50,
  "offset": 0,
  "returned": 1
}
```

### Get Single MarketEvent

**`GET /api/v1/market-events/{event_id}`**

Returns a single MarketEvent by its UUID.

- 200: Event found
- 404: Event not found

### Dashboard

**`GET /api/v1/dashboard`**

Returns a pre-aggregated dashboard summary — a single JSON document designed for the main screen of a future frontend. All aggregations are performed in SQLite, not by loading full tables into Python.

**Important**: This endpoint is READ-ONLY. It does not start RuntimeService, MasterEngine, or any detectors. It does not write to the database.

| Parameter | Type | Default | Min | Max | Description |
|-----------|------|---------|-----|-----|-------------|
| `latest_events_limit` | int | 10 | 1 | 50 | Max recent events to include |
| `top_tickers_limit` | int | 10 | 1 | 50 | Max top tickers to include |
| `activity_hours` | int | 24 | 1 | 168 | Hours window for aggregations |

#### Response Sections

- **`generated_at`** (string): ISO 8601 timestamp of response generation.
- **`system`** (object): API status, database availability, journal_mode, schema_version.
- **`runtime`** (object): cycle_count, event_count, last_cycle summary, is_empty flag.
- **`recent_activity`** (object): events_in_last_cycle, events_last_24h, unique_tickers, last_event_at.
- **`top_tickers`** (array): Most active tickers with event_count, last_event_at, priority_final.
- **`event_breakdown`** (object): by_event_family, by_event_type, by_priority (each an array of {key, count}).
- **`latest_events`** (array): Most recent MarketEvents with event_id, timestamp_utc, ticker, event_family, event_type, priority_final, confidence_level.

#### Example Response

```json
{
  "generated_at": "2026-07-20T18:30:00+00:00",
  "system": {
    "status": "ok",
    "database": "available",
    "journal_mode": "wal",
    "schema_version": 1
  },
  "runtime": {
    "cycle_count": 42,
    "event_count": 156,
    "last_cycle": {
      "cycle_id": "1721490000.0",
      "execution_time": 12.5,
      "candidates_count": 15,
      "success_count": 12,
      "error_count": 0,
      "status": "completed",
      "error_message": null,
      "created_at": "2026-07-20T18:20:00"
    },
    "last_cycle_at": "2026-07-20T18:20:00",
    "last_cycle_error_count": 0,
    "is_empty": false
  },
  "recent_activity": {
    "events_in_last_cycle": 4,
    "events_last_24h": 12,
    "unique_tickers_last_24h": 7,
    "last_event_at": "2026-07-20T18:19:10"
  },
  "top_tickers": [
    {
      "ticker": "XYZ.WA",
      "event_count": 5,
      "last_event_at": "2026-07-20T18:19:10",
      "priority_final": "HIGH"
    }
  ],
  "event_breakdown": {
    "by_event_family": [
      {"event_family": "PRICE", "count": 8},
      {"event_family": "VOLUME", "count": 4}
    ],
    "by_event_type": [
      {"event_type": "PRICE_SURGE", "count": 5},
      {"event_type": "VOLUME_SPIKE", "count": 3}
    ],
    "by_priority": [
      {"priority": "HIGH", "count": 6},
      {"priority": "MEDIUM", "count": 4}
    ]
  },
  "latest_events": [
    {
      "event_id": "a1b2c3d4-...",
      "timestamp_utc": "2026-07-20T18:19:10+00:00",
      "ticker": "XYZ.WA",
      "market": "GPW",
      "event_family": "PRICE",
      "event_type": "PRICE_SURGE",
      "priority_final": "CRITICAL",
      "confidence_level": 0.85
    }
  ]
}
```

#### Empty Database Behavior

When the database is empty, the endpoint still returns HTTP 200 with a valid structure:

```json
{
  "generated_at": "2026-07-20T18:30:00+00:00",
  "system": {
    "status": "ok",
    "database": "available",
    "journal_mode": "wal",
    "schema_version": 1
  },
  "runtime": {
    "cycle_count": 0,
    "event_count": 0,
    "last_cycle": null,
    "last_cycle_at": null,
    "last_cycle_error_count": null,
    "is_empty": true
  },
  "recent_activity": {
    "events_in_last_cycle": 0,
    "events_last_24h": 0,
    "unique_tickers_last_24h": 0,
    "last_event_at": null
  },
  "top_tickers": [],
  "event_breakdown": {
    "by_event_family": [],
    "by_event_type": [],
    "by_priority": []
  },
  "latest_events": []
}
```

#### Error Responses

| Status | Meaning |
|--------|---------|
| 422 | Invalid parameters (limit > 50, activity_hours > 168, negative values) |
| 503 | Database unavailable |
| 500 | Internal server error (no stack traces exposed) |

### Ticker MarketEvents

**`GET /api/v1/tickers/{ticker}/market-events`**

Returns MarketEvents for a specific ticker.

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Max events (default: 50, max: 200) |
| `offset` | int | Records to skip |
| `date_from` | str | ISO 8601 datetime filter |
| `date_to` | str | ISO 8601 datetime filter |

Ticker is normalized to uppercase. The original symbol meaning is preserved.

## Pagination

All list endpoints return a consistent paginated response:

```json
{
  "items": [...],
  "limit": 50,
  "offset": 0,
  "returned": 12
}
```

- `limit`: Requested limit (clamped to 200 max)
- `offset`: Requested offset (minimum 0)
- `returned`: Actual number of items in this response
- No endpoint returns the full table without limits

## Error Responses

| Status | Meaning |
|--------|---------|
| 400 | Invalid parameters (bad date format, negative values) |
| 404 | Resource not found (cycle, event) |
| 422 | Validation error (limit > 200, negative limit/offset) |
| 503 | Database unavailable |
| 500 | Internal server error (no stack traces exposed) |

Error responses are JSON with a `detail` field. No system paths, stack traces, or secrets are exposed.

## Important Notes

- **Read-only**: This API never writes to the database. It performs SELECT queries only.
- **Independent process**: The API and RuntimeService can run simultaneously as separate processes.
- **Same database**: Both processes use the same SQLite database file with WAL mode for safe concurrent access.
- **No engines**: The API does not start RuntimeService, MasterEngine, or any detectors.
- **No recommendations**: The API does not contain BUY/SELL logic or investment recommendations.