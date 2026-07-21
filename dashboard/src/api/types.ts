/**
 * TypeScript interfaces for all ALCHEMIK API responses.
 * Based on docs/API_README.md and actual api_entrypoint.py endpoints.
 */

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  api: string;
  database: string;
  journal_mode: string;
  schema_version: number;
  cycle_count: number;
  event_count: number;
}

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  items: T[];
  limit: number;
  offset: number;
  returned: number;
}

// ---------------------------------------------------------------------------
// Cycle
// ---------------------------------------------------------------------------

export interface CycleSummary {
  cycle_id: string;
  execution_time: number;
  candidates_count: number;
  success_count: number;
  error_count: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface CycleDetail extends CycleSummary {
  report: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// Runtime Statistics
// ---------------------------------------------------------------------------

export interface RuntimeStatistics {
  cycle_count: number;
  event_count: number;
  latest_cycle: CycleSummary | null;
  storage: {
    journal_mode: string;
    schema_version: number;
  };
}

// ---------------------------------------------------------------------------
// Market Event
// ---------------------------------------------------------------------------

export interface MarketEvent {
  event_id: string;
  timestamp_utc: string;
  ticker: string;
  market: string;
  instrument_type: string;
  event_family: string;
  event_category: string;
  event_type: string;
  priority_raw: string;
  priority_final: string;
  confidence_level: number;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export interface DashboardLastCycle {
  cycle_id: string;
  execution_time: number;
  candidates_count: number;
  success_count: number;
  error_count: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface DashboardRuntime {
  cycle_count: number;
  event_count: number;
  last_cycle: DashboardLastCycle | null;
  last_cycle_at: string | null;
  last_cycle_error_count: number | null;
  is_empty: boolean;
}

export interface DashboardSystem {
  status: string;
  database: string;
  journal_mode: string;
  schema_version: number;
}

export interface DashboardRecentActivity {
  events_in_last_cycle: number;
  events_last_24h: number;
  unique_tickers_last_24h: number;
  last_event_at: string | null;
}

export interface TopTicker {
  ticker: string;
  event_count: number;
  last_event_at: string;
  priority_final: string;
}

export interface EventBreakdownItem {
  event_family?: string;
  event_type?: string;
  priority?: string;
  key?: string;
  count: number;
}

export interface EventBreakdown {
  by_event_family: EventBreakdownItem[];
  by_event_type: EventBreakdownItem[];
  by_priority: EventBreakdownItem[];
}

export interface DashboardLatestEvent {
  event_id: string;
  timestamp_utc: string;
  ticker: string;
  market: string;
  event_family: string;
  event_type: string;
  priority_final: string;
  confidence_level: number;
}

export interface DashboardResponse {
  generated_at: string;
  system: DashboardSystem;
  runtime: DashboardRuntime;
  recent_activity: DashboardRecentActivity;
  top_tickers: TopTicker[];
  event_breakdown: EventBreakdown;
  latest_events: DashboardLatestEvent[];
}

// ---------------------------------------------------------------------------
// API Error
// ---------------------------------------------------------------------------

export interface ApiErrorResponse {
  detail: string;
}