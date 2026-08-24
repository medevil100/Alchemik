/**
 * Centralna konfiguracja adresu API i endpointów.
 *
 * KROK 8.4B — same-origin: klient używa wyłącznie względnego prefiksu `/api/v1`.
 * Żaden absolutny host nie trafia do bundle; proxy Vite (dev/preview) przekazuje
 * `/api` oraz `/health` do lokalnego FastAPI bez rewrite.
 */

function getBaseUrl(): string {
  // Względny prefiks — same-origin z dashboardem. Proxy Vite/Nginx obsługuje /api.
  return '/api/v1';
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
  DASHBOARD: '/dashboard',
  MARKET_EVENTS: '/market-events',
  MARKET_EVENT_BY_ID: (id: string) => `/market-events/${encodeURIComponent(id)}`,
  CYCLES: '/cycles',
  CYCLE_BY_ID: (id: string) => `/cycles/${encodeURIComponent(id)}`,
  RUNTIME_STATISTICS: '/runtime/statistics',
  TICKER_EVENTS: (ticker: string) =>
    `/tickers/${encodeURIComponent(ticker)}/market-events`,
} as const;