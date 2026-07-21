import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchDashboard } from '../api/api';
import type { DashboardResponse } from '../api/types';

export interface DashboardState {
  data: DashboardResponse | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

export interface UseDashboardReturn extends DashboardState {
  _checkForTest: () => Promise<void>;
}

const POLLING_INTERVAL_MS = 30_000;

export function useDashboard(): UseDashboardReturn {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const mountedRef = useRef(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const check = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchDashboard();
      if (!mountedRef.current) return;
      setData(result);
      setLastUpdated(new Date());
    } catch (err: unknown) {
      if (!mountedRef.current) return;
      const message = err instanceof Error ? err.message : 'Nieznany błąd podczas pobierania dashboardu';
      setError(message);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    // Pierwsze pobranie natychmiast po zamontowaniu
    check();

    // Polling co 30 sekund zgodnie z docs/ETAP_5_ARCHITEKTURA_FRONTENDU.md
    intervalRef.current = setInterval(() => {
      check();
    }, POLLING_INTERVAL_MS);

    return () => {
      mountedRef.current = false;
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [check]);

  return { data, loading, error, lastUpdated, _checkForTest: check };
}