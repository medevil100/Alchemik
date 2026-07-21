import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useDashboard } from '../useDashboard';
import type { DashboardResponse } from '../../api/types';

let mockResponse: DashboardResponse;
let mockError: Error | null;

vi.mock('../../api/api', () => ({
  fetchDashboard: vi.fn().mockImplementation(() => {
    if (mockError) throw mockError;
    return Promise.resolve(mockResponse);
  }),
}));

function buildDashboard(overrides: Partial<DashboardResponse> = {}): DashboardResponse {
  return {
    generated_at: '2026-07-21T18:00:00+00:00',
    system: {
      status: 'ok',
      database: 'available',
      journal_mode: 'wal',
      schema_version: 1,
    },
    runtime: {
      cycle_count: 42,
      event_count: 156,
      last_cycle: {
        cycle_id: '1721490000.0',
        execution_time: 12.5,
        candidates_count: 15,
        success_count: 12,
        error_count: 0,
        status: 'completed',
        error_message: null,
        created_at: '2026-07-21T17:50:00',
      },
      last_cycle_at: '2026-07-21T17:50:00',
      last_cycle_error_count: 0,
      is_empty: false,
    },
    recent_activity: {
      events_in_last_cycle: 4,
      events_last_24h: 12,
      unique_tickers_last_24h: 7,
      last_event_at: '2026-07-21T17:49:10',
    },
    top_tickers: [
      {
        ticker: 'XYZ.WA',
        event_count: 5,
        last_event_at: '2026-07-21T17:49:10',
        priority_final: 'HIGH',
      },
    ],
    event_breakdown: {
      by_event_family: [{ event_family: 'PRICE', count: 8 }],
      by_event_type: [{ event_type: 'PRICE_SURGE', count: 5 }],
      by_priority: [{ priority: 'HIGH', count: 6 }],
    },
    latest_events: [
      {
        event_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        timestamp_utc: '2026-07-21T17:49:10+00:00',
        ticker: 'XYZ.WA',
        market: 'GPW',
        event_family: 'PRICE',
        event_type: 'PRICE_SURGE',
        priority_final: 'CRITICAL',
        confidence_level: 0.85,
      },
    ],
    ...overrides,
  };
}

describe('useDashboard', () => {
  beforeEach(() => {
    mockResponse = buildDashboard();
    mockError = null;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('początkowo ma loading=true i data=null', () => {
    const { result } = renderHook(() => useDashboard());
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('ustawia dane po pomyślnym pobraniu', async () => {
    const { result } = renderHook(() => useDashboard());
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
    expect(result.current.lastUpdated).toBeInstanceOf(Date);
  });

  it('ustawia błąd gdy fetchDashboard rzuci wyjątek', async () => {
    mockError = new Error('Backend niedostępny');
    const { result } = renderHook(() => useDashboard());
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe('Backend niedostępny');
  });

  it('nie aktualizuje stanu po odmontowaniu', async () => {
    const { result, unmount } = renderHook(() => useDashboard());
    unmount();
    // Powinno się zakończyć bez eksplozji — nie sprawdzamy stanu po unmount
    await vi.waitFor(() => {
      // Component unmounted, nic nie powinno się zepsuć
    }, { timeout: 1000 });
    expect(result.current.data).toBeNull();
  });

  it('czyści interwał przy odmontowaniu', () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    const { unmount } = renderHook(() => useDashboard());
    unmount();
    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});