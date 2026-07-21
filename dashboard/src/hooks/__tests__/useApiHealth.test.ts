import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useApiHealth } from '../useApiHealth';

const mockFetchHealth = vi.fn();

vi.mock('../../api/api', () => ({
  fetchHealth: (...args: unknown[]) => mockFetchHealth(...args),
}));

const HEALTH_OK = {
  status: 'ok',
  api: 'running',
  database: 'connected',
  journal_mode: 'wal',
  schema_version: 1,
  cycle_count: 42,
  event_count: 128,
};

describe('useApiHealth', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockFetchHealth.mockReset();
    mockFetchHealth.mockResolvedValue(HEALTH_OK);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('performs first health check immediately on mount', async () => {
    renderHook(() => useApiHealth());

    await waitFor(() => {
      expect(mockFetchHealth).toHaveBeenCalled();
    });
  });

  it('automatically re-checks every 10 seconds', async () => {
    renderHook(() => useApiHealth());

    // Let the first call settle
    await waitFor(() => {
      expect(mockFetchHealth).toHaveBeenCalled();
    });
    const afterMount = mockFetchHealth.mock.calls.length;

    // Advance 10 s — interval fires, then wait for fetch
    act(() => {
      vi.advanceTimersByTime(10_000);
    });

    await waitFor(() => {
      expect(mockFetchHealth).toHaveBeenCalledTimes(afterMount + 1);
    });

    // Another 10 s
    act(() => {
      vi.advanceTimersByTime(10_000);
    });

    await waitFor(() => {
      expect(mockFetchHealth).toHaveBeenCalledTimes(afterMount + 2);
    });
  });

  it('has only one interval (no double polling)', async () => {
    renderHook(() => useApiHealth());

    await waitFor(() => {
      expect(mockFetchHealth).toHaveBeenCalled();
    });
    const before = mockFetchHealth.mock.calls.length;

    act(() => {
      vi.advanceTimersByTime(10_000);
    });

    await waitFor(() => {
      expect(mockFetchHealth).toHaveBeenCalledTimes(before + 1);
    });
  });

  it('clears interval on unmount', async () => {
    const { unmount } = renderHook(() => useApiHealth());

    await waitFor(() => {
      expect(mockFetchHealth).toHaveBeenCalled();
    });
    const before = mockFetchHealth.mock.calls.length;

    unmount();

    // Advance far past several intervals
    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    // No new calls should have been made
    expect(mockFetchHealth).toHaveBeenCalledTimes(before);
  });

  it('does not update state after unmount', async () => {
    let resolvePending!: (v: unknown) => void;
    const delayed = new Promise<unknown>((resolve) => {
      resolvePending = resolve;
    });
    mockFetchHealth.mockReturnValue(delayed);

    const { unmount, result } = renderHook(() => useApiHealth());

    unmount();

    await act(async () => {
      resolvePending(HEALTH_OK);
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.status).toBe('checking');
  });

  it('handles success state', async () => {
    mockFetchHealth.mockResolvedValue({
      ...HEALTH_OK,
      schema_version: 2,
      cycle_count: 10,
    });

    const { result } = renderHook(() => useApiHealth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.status).toBe('online');
    expect(result.current.error).toBeNull();
    expect(result.current.health?.schema_version).toBe(2);
  });

  it('handles error state', async () => {
    mockFetchHealth.mockRejectedValue(new Error('Sieć niedostępna'));

    const { result } = renderHook(() => useApiHealth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.status).toBe('offline');
    expect(result.current.error).toBe('Sieć niedostępna');
    expect(result.current.health).toBeNull();
  });

  it('handles loading state during initial check', async () => {
    let resolvePending!: (v: unknown) => void;
    const delayed = new Promise<unknown>((resolve) => {
      resolvePending = resolve;
    });
    mockFetchHealth.mockReturnValue(delayed);

    const { result } = renderHook(() => useApiHealth());

    expect(result.current.loading).toBe(true);
    expect(result.current.status).toBe('checking');

    await act(async () => {
      resolvePending(HEALTH_OK);
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.status).toBe('online');
  });

  it('handles no-data state (health null after error)', async () => {
    const { result } = renderHook(() => useApiHealth());

    await waitFor(() => {
      expect(result.current.health).not.toBeNull();
    });

    // Change mock to fail on next interval call
    mockFetchHealth.mockReset();
    mockFetchHealth.mockRejectedValue(new Error('Brak połączenia'));

    act(() => {
      vi.advanceTimersByTime(10_000);
    });

    await waitFor(() => {
      expect(result.current.status).toBe('offline');
    });

    expect(result.current.health).toBeNull();
    expect(result.current.error).toBe('Brak połączenia');
  });
});