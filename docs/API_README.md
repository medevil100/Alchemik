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