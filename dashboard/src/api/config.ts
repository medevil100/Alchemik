/**
 * Centralna konfiguracja adresu API i endpointów.
 * Adres API jest konfigurowalny przez zmienną środowiskową VITE_API_URL.
 */

function getBaseUrl(): string {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // W development: Vite proxy kieruje /api i /health na localhost:8000
  return '';
}

export const API_CONFIG = {
  BASE_URL: getBaseUrl(),
  TIMEOUT_MS: 10_000,
  POLLING_INTERVAL_MS: 30_000,
  LIST_POLLING_INTERVAL_MS: 60_000,
  DEFAULT_PAGE_LIMIT: 50,
  MAX_PAGE_LIMIT: 200,
} as const;

export const ENDPOINTS = {
  HEALTH: '/health',
  DASHBOARD: '/api/v1/dashboard',
  MARKET_EVENTS: '/api/v1/market-events',
  MARKET_EVENT_BY_ID: (id: string) => `/api/v1/market-events/${encodeURIComponent(id)}`,
  CYCLES: '/api/v1/cycles',
  CYCLE_BY_ID: (id: string) => `/api/v1/cycles/${encodeURIComponent(id)}`,
  RUNTIME_STATISTICS: '/api/v1/runtime/statistics',
  TICKER_EVENTS: (ticker: string) =>
    `/api/v1/tickers/${encodeURIComponent(ticker)}/market-events`,
} as const;