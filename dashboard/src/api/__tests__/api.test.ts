import { describe, it, expect } from 'vitest';
import {
  ENDPOINTS,
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

describe('ENDPOINTS', () => {
  it('ENDPOINTS.HEALTH to /health', () => {
    expect(ENDPOINTS.HEALTH).toBe('/health');
  });

  it('ENDPOINTS.DASHBOARD to /api/v1/dashboard', () => {
    expect(ENDPOINTS.DASHBOARD).toBe('/api/v1/dashboard');
  });

  it('ENDPOINTS.MARKET_EVENTS to /api/v1/market-events', () => {
    expect(ENDPOINTS.MARKET_EVENTS).toBe('/api/v1/market-events');
  });

  it('ENDPOINTS.MARKET_EVENT_BY_ID generuje poprawną ścieżkę', () => {
    expect(ENDPOINTS.MARKET_EVENT_BY_ID('evt-001')).toBe('/api/v1/market-events/evt-001');
  });

  it('ENDPOINTS.CYCLES to /api/v1/cycles', () => {
    expect(ENDPOINTS.CYCLES).toBe('/api/v1/cycles');
  });

  it('ENDPOINTS.CYCLE_BY_ID generuje poprawną ścieżkę', () => {
    expect(ENDPOINTS.CYCLE_BY_ID('cycle-42')).toBe('/api/v1/cycles/cycle-42');
  });

  it('ENDPOINTS.RUNTIME_STATISTICS to /api/v1/runtime/statistics', () => {
    expect(ENDPOINTS.RUNTIME_STATISTICS).toBe('/api/v1/runtime/statistics');
  });

  it('ENDPOINTS.TICKER_EVENTS generuje poprawną ścieżkę z tickerem', () => {
    expect(ENDPOINTS.TICKER_EVENTS('ABC.WA')).toBe('/api/v1/tickers/ABC.WA/market-events');
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