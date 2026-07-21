import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useMarketEvents } from '../useMarketEvents';
import type { PaginatedResponse, MarketEvent } from '../../api/types';

let mockResponse: PaginatedResponse<MarketEvent>;
let mockError: Error | null;

const { fetchMarketEventsMock } = vi.hoisted(() => ({
  fetchMarketEventsMock: vi.fn(),
}));

vi.mock('../../api/api', () => ({
  fetchMarketEvents: fetchMarketEventsMock,
}));

function buildEvent(overrides: Partial<MarketEvent> = {}): MarketEvent {
  return {
    event_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    timestamp_utc: '2026-07-21T17:49:10+00:00',
    ticker: 'XYZ.WA',
    market: 'GPW',
    instrument_type: 'STOCK_GPW',
    event_family: 'PRICE',
    event_category: 'Cenowe',
    event_type: 'PRICE_SURGE',
    priority_raw: 'HIGH',
    priority_final: 'CRITICAL',
    confidence_level: 0.85,
    ...overrides,
  };
}

function buildResponse(
  items: MarketEvent[],
  overrides: Partial<PaginatedResponse<MarketEvent>> = {},
): PaginatedResponse<MarketEvent> {
  return {
    items,
    limit: 50,
    offset: 0,
    returned: items.length,
    ...overrides,
  };
}

describe('useMarketEvents', () => {
  beforeEach(() => {
    mockResponse = buildResponse([buildEvent()]);
    mockError = null;
    fetchMarketEventsMock.mockImplementation(() => {
      if (mockError) throw mockError;
      return Promise.resolve(mockResponse);
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // --- Initial state ---

  it('początkowo ma loading=true i data=null', () => {
    const { result } = renderHook(() => useMarketEvents());
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  // --- Success ---

  it('ustawia dane po pomyślnym pobraniu', async () => {
    const { result } = renderHook(() => useMarketEvents());
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it('przekazuje poprawne parametry API', async () => {
    const { result } = renderHook(() =>
      useMarketEvents({ limit: 50, offset: 0 }),
    );
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(fetchMarketEventsMock).toHaveBeenCalledWith(
      expect.objectContaining({ limit: 50, offset: 0 }),
    );
  });

  // --- Empty list ---

  it('obsługuje pustą listę zdarzeń', async () => {
    mockResponse = buildResponse([]);
    const { result } = renderHook(() => useMarketEvents());
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data).toEqual(mockResponse);
    expect(result.current.data!.items).toHaveLength(0);
  });

  // --- Error on first fetch ---

  it('ustawia błąd gdy fetchMarketEvents rzuci wyjątek', async () => {
    mockError = new Error('Backend niedostępny');
    const { result } = renderHook(() => useMarketEvents());
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe('Backend niedostępny');
  });

  // --- Cleanup ---

  it('czyści interwał przy odmontowaniu', () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    const { unmount } = renderHook(() => useMarketEvents());
    unmount();
    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });

  it('nie aktualizuje stanu po odmontowaniu', async () => {
    let resolveFetch: (v: PaginatedResponse<MarketEvent>) => void;
    fetchMarketEventsMock.mockReturnValue(
      new Promise<PaginatedResponse<MarketEvent>>((resolve) => {
        resolveFetch = resolve;
      }),
    );

    const { result, unmount } = renderHook(() => useMarketEvents());
    unmount();

    await act(async () => {
      resolveFetch!(mockResponse);
    });

    expect(result.current.data).toBeNull();
  });

  // --- Preserve data on polling error ---

  it('zachowuje dane po błędzie setParams', async () => {
    const { result } = renderHook(() => useMarketEvents());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data).toEqual(mockResponse);
    expect(result.current.error).toBeNull();

    mockError = new Error('Błąd sieci');

    act(() => {
      result.current.setParams({ offset: 0 });
    });

    await waitFor(() => {
      expect(result.current.error).toBe('Błąd sieci');
    });

    expect(result.current.data).toEqual(mockResponse);
  });

  // --- setParams ---

  it('setParams resetuje offset przy zmianie filtrów', async () => {
    const { result } = renderHook(() => useMarketEvents());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    fetchMarketEventsMock.mockClear();

    act(() => {
      result.current.setParams({ ticker: 'ABC.WA', offset: 50 });
    });

    await waitFor(() => {
      expect(fetchMarketEventsMock).toHaveBeenCalledWith(
        expect.objectContaining({ ticker: 'ABC.WA', offset: 0 }),
      );
    });
  });

  it('setParams nie resetuje offsetu przy zmianie tylko strony', async () => {
    const { result } = renderHook(() => useMarketEvents());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    fetchMarketEventsMock.mockClear();

    act(() => {
      result.current.setParams({ offset: 50 });
    });

    await waitFor(() => {
      expect(fetchMarketEventsMock).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 50 }),
      );
    });
  });

  // --- Single interval ---

  it('tworzy dokładnie jeden interwał', () => {
    const setIntervalSpy = vi.spyOn(globalThis, 'setInterval');
    const { unmount } = renderHook(() => useMarketEvents());

    const ourCalls = setIntervalSpy.mock.calls.filter(
      ([, ms]) => ms === 60_000,
    );
    expect(ourCalls.length).toBe(1);

    setIntervalSpy.mockRestore();
    unmount();
  });

  it('zmiana filtrów nie tworzy dodatkowego interwału', async () => {
    const setIntervalSpy = vi.spyOn(globalThis, 'setInterval');

    const { result } = renderHook(() => useMarketEvents());
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const initialCallCount = setIntervalSpy.mock.calls.filter(
      ([, ms]) => ms === 60_000,
    ).length;

    act(() => {
      result.current.setParams({ ticker: 'ABC.WA' });
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const afterCallCount = setIntervalSpy.mock.calls.filter(
      ([, ms]) => ms === 60_000,
    ).length;
    expect(afterCallCount).toBe(initialCallCount);

    setIntervalSpy.mockRestore();
  });

  it('zmiana strony nie tworzy dodatkowego interwału', async () => {
    const setIntervalSpy = vi.spyOn(globalThis, 'setInterval');

    const { result } = renderHook(() => useMarketEvents());
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const initialCallCount = setIntervalSpy.mock.calls.filter(
      ([, ms]) => ms === 60_000,
    ).length;

    act(() => {
      result.current.setParams({ offset: 50 });
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const afterCallCount = setIntervalSpy.mock.calls.filter(
      ([, ms]) => ms === 60_000,
    ).length;
    expect(afterCallCount).toBe(initialCallCount);

    setIntervalSpy.mockRestore();
  });

  // --- loadMore (mobile accumulation) ---

  it('loadMore dokleja rekordy i nie tworzy duplikatów', async () => {
    const firstPage = buildResponse(
      [buildEvent({ event_id: 'evt-1', ticker: 'AAA.WA' })],
      { limit: 50, offset: 0, returned: 1 },
    );
    mockResponse = firstPage;

    const { result } = renderHook(() => useMarketEvents());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data!.items).toHaveLength(1);

    // Now load more
    mockResponse = buildResponse(
      [buildEvent({ event_id: 'evt-2', ticker: 'BBB.WA' })],
      { limit: 50, offset: 50, returned: 1 },
    );

    await act(async () => {
      result.current.loadMore(50);
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data!.items).toHaveLength(2);
    expect(result.current.data!.items[0].ticker).toBe('AAA.WA');
    expect(result.current.data!.items[1].ticker).toBe('BBB.WA');
  });

  it('loadMore nie zmienia danych gdy kolejna strona jest pusta', async () => {
    mockResponse = buildResponse(
      [buildEvent({ event_id: 'evt-1', ticker: 'AAA.WA' })],
      { limit: 50, offset: 0, returned: 1 },
    );

    const { result } = renderHook(() => useMarketEvents());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Empty next page
    mockResponse = buildResponse([], { limit: 50, offset: 50, returned: 0 });

    await act(async () => {
      result.current.loadMore(50);
    });

    // Data unchanged — still has the first event
    expect(result.current.data!.items).toHaveLength(1);
    expect(result.current.data!.items[0].ticker).toBe('AAA.WA');
  });
});