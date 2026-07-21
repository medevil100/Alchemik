/**
 * Funkcje mapujące wszystkie istniejące endpointy REST API.
 * Żaden komponent UI nie powinien wywoływać bezpośrednio fetch().
 */

import { get } from './client';
import { ENDPOINTS } from './config';
import type {
  HealthResponse,
  PaginatedResponse,
  CycleSummary,
  CycleDetail,
  RuntimeStatistics,
  MarketEvent,
  DashboardResponse,
} from './types';

// ---------------------------------------------------------------------------
// Parametry
// ---------------------------------------------------------------------------

export interface ListParams {
  limit?: number;
  offset?: number;
}

export interface DashboardParams {
  latest_events_limit?: number;
  top_tickers_limit?: number;
  activity_hours?: number;
}

export interface EventListParams extends ListParams {
  ticker?: string;
  market?: string;
  instrument_type?: string;
  event_family?: string;
  event_type?: string;
  priority_final?: string;
  date_from?: string;
  date_to?: string;
}

export interface TickerEventParams extends ListParams {
  date_from?: string;
  date_to?: string;
}

// ---------------------------------------------------------------------------
// Funkcje API
// ---------------------------------------------------------------------------

export function fetchHealth(): Promise<HealthResponse> {
  return get<HealthResponse>(ENDPOINTS.HEALTH);
}

export function fetchDashboard(params?: DashboardParams): Promise<DashboardResponse> {
  return get<DashboardResponse>(ENDPOINTS.DASHBOARD, params as Record<string, string | number | undefined>);
}

export function fetchMarketEvents(params?: EventListParams): Promise<PaginatedResponse<MarketEvent>> {
  return get<PaginatedResponse<MarketEvent>>(ENDPOINTS.MARKET_EVENTS, params as Record<string, string | number | undefined>);
}

export function fetchMarketEventById(id: string): Promise<MarketEvent> {
  return get<MarketEvent>(ENDPOINTS.MARKET_EVENT_BY_ID(id));
}

export function fetchCycles(params?: ListParams): Promise<PaginatedResponse<CycleSummary>> {
  return get<PaginatedResponse<CycleSummary>>(ENDPOINTS.CYCLES, params as Record<string, string | number | undefined>);
}

export function fetchCycleById(id: string): Promise<CycleDetail> {
  return get<CycleDetail>(ENDPOINTS.CYCLE_BY_ID(id));
}

export function fetchRuntimeStatistics(): Promise<RuntimeStatistics> {
  return get<RuntimeStatistics>(ENDPOINTS.RUNTIME_STATISTICS);
}

export function fetchTickerEvents(
  ticker: string,
  params?: TickerEventParams,
): Promise<PaginatedResponse<MarketEvent>> {
  return get<PaginatedResponse<MarketEvent>>(
    ENDPOINTS.TICKER_EVENTS(ticker),
    params as Record<string, string | number | undefined>,
  );
}