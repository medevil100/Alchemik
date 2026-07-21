import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchMarketEvents } from '../api/api';
import type { MarketEvent, PaginatedResponse } from '../api/types';
import type { EventListParams } from '../api/api';
import { API_CONFIG } from '../api/config';

export interface MarketEventsState {
  data: PaginatedResponse<MarketEvent> | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

export interface UseMarketEventsReturn extends MarketEventsState {
  /**
   * Update filters, offset, or limit. Resets offset to 0 when filters change.
   * Triggers a new fetch immediately. Replaces all data.
   */
  setParams: (params: EventListParams) => void;

  /**
   * Load more events — appends results to the current list.
   * Used by mobile "Załaduj więcej". Accumulates items.
   * If the next page returns 0 items, data is NOT changed.
   */
  loadMore: (nextOffset: number) => void;
}

const POLLING_INTERVAL_MS = API_CONFIG.LIST_POLLING_INTERVAL_MS;

export function useMarketEvents(
  initialParams: EventListParams = {},
): UseMarketEventsReturn {
  const [data, setData] = useState<PaginatedResponse<MarketEvent> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [params, setParamsState] = useState<EventListParams>(() => ({
    limit: initialParams.limit ?? API_CONFIG.DEFAULT_PAGE_LIMIT,
    offset: initialParams.offset ?? 0,
    ...initialParams,
  }));

  const mountedRef = useRef(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const paramsRef = useRef(params);
  // Track accumulated items for mobile "load more"
  const accumulatedRef = useRef<MarketEvent[] | null>(null);

  // Keep paramsRef in sync so the polling interval always sees the latest params.
  paramsRef.current = params;

  const check = useCallback(async (currentParams: EventListParams) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchMarketEvents(currentParams);
      if (!mountedRef.current) return;
      setData(result);
      setLastUpdated(new Date());
    } catch (err: unknown) {
      if (!mountedRef.current) return;
      const message =
        err instanceof Error ? err.message : 'Nieznany błąd podczas pobierania zdarzeń rynkowych';
      setError(message);
      // Keep previous data so the view doesn't collapse on a polling error.
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  // setParams — replace data (desktop pagination, filtering)
  const setParams = useCallback(
    (newParams: EventListParams) => {
      accumulatedRef.current = null; // reset accumulation

      const { offset: _newOff, limit: _newLim, ...newFilters } = newParams;
      const { offset: _oldOff, limit: _oldLim, ...oldFilters } = paramsRef.current;

      const filtersChanged =
        JSON.stringify(newFilters) !== JSON.stringify(oldFilters);

      const merged: EventListParams = {
        limit: newParams.limit ?? API_CONFIG.DEFAULT_PAGE_LIMIT,
        offset: filtersChanged ? 0 : (newParams.offset ?? paramsRef.current.offset),
        ...newFilters,
      };

      setParamsState(merged);
      check(merged);
    },
    [check],
  );

  // loadMore — append data (mobile "Załaduj więcej")
  const loadMore = useCallback(
    async (nextOffset: number) => {
      setLoading(true);
      setError(null);
      try {
        const currentParams = {
          ...paramsRef.current,
          offset: nextOffset,
          limit: paramsRef.current.limit ?? API_CONFIG.DEFAULT_PAGE_LIMIT,
        };
        const result = await fetchMarketEvents(currentParams);
        if (!mountedRef.current) return;

        // Only accumulate if we got items
        if (result.items.length > 0) {
          const prev = accumulatedRef.current ?? data?.items ?? [];
          accumulatedRef.current = [...prev, ...result.items];

          setData({
            ...result,
            items: accumulatedRef.current,
            returned: accumulatedRef.current.length,
            // Keep the last page's offset/limit for pagination
            limit: result.limit,
            offset: result.offset,
          });
        } else {
          // Empty response — don't change data, can't load more
          // Keep current data untouched
        }
        setLastUpdated(new Date());
      } catch (err: unknown) {
        if (!mountedRef.current) return;
        const message =
          err instanceof Error ? err.message : 'Nieznany błąd podczas pobierania zdarzeń rynkowych';
        setError(message);
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    },
    [data],
  );

  // Initial fetch on mount + one polling interval.
  useEffect(() => {
    mountedRef.current = true;

    check(params);

    intervalRef.current = setInterval(() => {
      check(paramsRef.current);
    }, POLLING_INTERVAL_MS);

    return () => {
      mountedRef.current = false;
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading, error, lastUpdated, setParams, loadMore };
}