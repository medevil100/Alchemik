import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchHealth } from '../api/api';
import type { HealthResponse } from '../api/types';

export type ConnectionStatus = 'checking' | 'online' | 'offline';

export interface HealthState {
  status: ConnectionStatus;
  health: HealthResponse | null;
  error: string | null;
  lastChecked: Date | null;
  loading: boolean;
}

export interface UseApiHealthReturn extends HealthState {
  /** Exposed for tests only — manually triggers a single health check. */
  _checkForTest: () => Promise<void>;
}

const POLLING_INTERVAL_MS = 10_000;

export function useApiHealth(): UseApiHealthReturn {
  const [status, setStatus] = useState<ConnectionStatus>('checking');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);

  const mountedRef = useRef(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const check = useCallback(async () => {
    setLoading(true);
    setStatus('checking');
    setError(null);
    try {
      const result = await fetchHealth();
      if (!mountedRef.current) return;
      setHealth(result);
      setStatus('online');
      setLastChecked(new Date());
    } catch (err: unknown) {
      if (!mountedRef.current) return;
      setHealth(null);
      setStatus('offline');
      const message = err instanceof Error ? err.message : 'Nieznany błąd';
      setError(message);
      setLastChecked(new Date());
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    // Pierwsze zapytanie natychmiast po uruchomieniu
    check();

    // Automatyczne ponawianie co 10 sekund
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

  return { status, health, error, lastChecked, loading, _checkForTest: check };
}