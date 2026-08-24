import { describe, it, expect } from 'vitest';
import {
  ENDPOINTS,
  API_CONFIG,
} from '../config';
import {
  fetchHealth,
  fetchDashboard,
  fetchMarketEvents,
  fetchMarketEventById,
  fetchCycles,
  fetchCycleById,
  fetchRuntimeStatistics,
  fetchTickerEvents,
} from '../api';

describe('ENDPOINTS (KROK 8.4B — ścieżki względem base /api/v1)', () => {
  it('BASE_URL to /api/v1 (bez hosta, bez końcowego slash) — brak podwójnego prefiksu', () => {
    expect(API_CONFIG.BASE_URL).toBe('/api/v1');
    expect(API_CONFIG.BASE_URL.endsWith('/')).toBe(false);
    expect(API_CONFIG.BASE_URL).not.toMatch(/\/\//);
  });

  it('ENDPOINTS.HEALTH to /health (osobno, poza base /api/v1)', () => {
    expect(ENDPOINTS.HEALTH).toBe('/health');
  });

  it('ENDPOINTS.DASHBOARD to /dashboard (złożenie -> /api/v1/dashboard)', () => {
    expect(ENDPOINTS.DASHBOARD).toBe('/dashboard');
    expect(`${API_CONFIG.BASE_URL}${ENDPOINTS.DASHBOARD}`).toBe('/api/v1/dashboard');
  });

  it('ENDPOINTS.MARKET_EVENTS to /market-events', () => {
    expect(ENDPOINTS.MARKET_EVENTS).toBe('/market-events');
    expect(`${API_CONFIG.BASE_URL}${ENDPOINTS.MARKET_EVENTS}`).toBe('/api/v1/market-events');
  });

  it('ENDPOINTS.MARKET_EVENT_BY_ID generuje poprawną ścieżkę', () => {
    expect(ENDPOINTS.MARKET_EVENT_BY_ID('evt-001')).toBe('/market-events/evt-001');
    expect(`${API_CONFIG.BASE_URL}${ENDPOINTS.MARKET_EVENT_BY_ID('evt-001')}`).toBe('/api/v1/market-events/evt-001');
  });

  it('ENDPOINTS.CYCLES to /cycles', () => {
    expect(ENDPOINTS.CYCLES).toBe('/cycles');
    expect(`${API_CONFIG.BASE_URL}${ENDPOINTS.CYCLES}`).toBe('/api/v1/cycles');
  });

  it('ENDPOINTS.CYCLE_BY_ID generuje poprawną ścieżkę', () => {
    expect(ENDPOINTS.CYCLE_BY_ID('cycle-42')).toBe('/cycles/cycle-42');
    expect(`${API_CONFIG.BASE_URL}${ENDPOINTS.CYCLE_BY_ID('cycle-42')}`).toBe('/api/v1/cycles/cycle-42');
  });

  it('ENDPOINTS.RUNTIME_STATISTICS to /runtime/statistics', () => {
    expect(ENDPOINTS.RUNTIME_STATISTICS).toBe('/runtime/statistics');
    expect(`${API_CONFIG.BASE_URL}${ENDPOINTS.RUNTIME_STATISTICS}`).toBe('/api/v1/runtime/statistics');
  });

  it('ENDPOINTS.TICKER_EVENTS generuje poprawną ścieżkę z tickerem', () => {
    expect(ENDPOINTS.TICKER_EVENTS('ABC.WA')).toBe('/tickers/ABC.WA/market-events');
    expect(`${API_CONFIG.BASE_URL}${ENDPOINTS.TICKER_EVENTS('ABC.WA')}`).toBe('/api/v1/tickers/ABC.WA/market-events');
  });
});

describe('fetch functions exist', () => {
  it('fetchHealth is a function', () => {
    expect(typeof fetchHealth).toBe('function');
  });

  it('fetchDashboard is a function', () => {
    expect(typeof fetchDashboard).toBe('function');
  });

  it('fetchMarketEvents is a function', () => {
    expect(typeof fetchMarketEvents).toBe('function');
  });

  it('fetchMarketEventById is a function', () => {
    expect(typeof fetchMarketEventById).toBe('function');
  });

  it('fetchCycles is a function', () => {
    expect(typeof fetchCycles).toBe('function');
  });

  it('fetchCycleById is a function', () => {
    expect(typeof fetchCycleById).toBe('function');
  });

  it('fetchRuntimeStatistics is a function', () => {
    expect(typeof fetchRuntimeStatistics).toBe('function');
  });

  it('fetchTickerEvents is a function', () => {
    expect(typeof fetchTickerEvents).toBe('function');
  });
});