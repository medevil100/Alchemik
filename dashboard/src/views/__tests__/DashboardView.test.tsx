import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import DashboardView from '../DashboardView';
import type { DashboardResponse } from '../../api/types';

const { useDashboardMock } = vi.hoisted(() => ({
  useDashboardMock: vi.fn(),
}));

vi.mock('../../hooks/useDashboard', () => ({
  useDashboard: useDashboardMock,
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

function mockReturn(data: DashboardResponse | null, loading: boolean, error: string | null) {
  useDashboardMock.mockReturnValue({
    data,
    loading,
    error,
    lastUpdated: data ? new Date() : null,
    _checkForTest: vi.fn(),
  });
}

describe('DashboardView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('wyświetla LoadingSpinner w stanie ładowania', () => {
    mockReturn(null, true, null);
    render(<DashboardView />);
    expect(screen.getByText('Ładowanie panelu głównego…')).toBeInTheDocument();
  });

  it('wyświetla ErrorBanner gdy wystąpi błąd i brak danych', () => {
    mockReturn(null, false, 'Backend niedostępny');
    render(<DashboardView />);
    expect(screen.getByText('Nie udało się załadować panelu głównego.')).toBeInTheDocument();
  });

  it('wyświetla EmptyState gdy baza jest pusta (is_empty: true)', () => {
    const emptyDashboard = buildDashboard({ runtime: { ...buildDashboard().runtime, is_empty: true } });
    mockReturn(emptyDashboard, false, null);
    render(<DashboardView />);
    expect(screen.getByText('Brak danych')).toBeInTheDocument();
    expect(
      screen.getByText('System oczekuje na pierwszy cykl Runtime. To może potrwać do 15 minut od uruchomienia.'),
    ).toBeInTheDocument();
  });

  it('wyświetla tytuł Pulpit i karty z danymi w stanie sukcesu', () => {
    const data = buildDashboard();
    mockReturn(data, false, null);
    render(<DashboardView />);

    expect(screen.getByText('Pulpit')).toBeInTheDocument();
    // Sprawdzenie hierarchii nagłówków: h1 dla tytułu, h2 dla kart
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Pulpit');
    const h2s = screen.getAllByRole('heading', { level: 2 });
    expect(h2s.length).toBe(7);
    expect(h2s[0]).toHaveTextContent('System');
    expect(h2s[1]).toHaveTextContent('Runtime');
    expect(h2s[2]).toHaveTextContent('Ostatnia aktywność');

    expect(screen.getByText('System')).toBeInTheDocument();
    expect(screen.getByText('Runtime')).toBeInTheDocument();
    expect(screen.getByText('Ostatnia aktywność')).toBeInTheDocument();
    expect(screen.getByText('Najaktywniejsze tickery')).toBeInTheDocument();
    expect(screen.getByText('Podział zdarzeń wg rodziny')).toBeInTheDocument();
    expect(screen.getByText('Podział zdarzeń wg priorytetu')).toBeInTheDocument();
    expect(screen.getByText('Najnowsze zdarzenia')).toBeInTheDocument();

    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('156')).toBeInTheDocument();
    expect(screen.getAllByText('XYZ.WA')).toHaveLength(2);
    expect(screen.getAllByText('PRICE')).toHaveLength(2);
    expect(screen.getByText('PRICE_SURGE')).toBeInTheDocument();
    expect(screen.getByText('Krytyczny')).toBeInTheDocument();
  });

  it('wyświetla informację o braku tickerów gdy top_tickers jest puste', () => {
    const noTickers = buildDashboard({ top_tickers: [] });
    mockReturn(noTickers, false, null);
    render(<DashboardView />);
    expect(screen.getByText('Brak tickerów w wybranym oknie czasowym.')).toBeInTheDocument();
  });

  it('wyświetla ErrorBanner z błędem odświeżania gdy error i data istnieją', () => {
    const data = buildDashboard();
    mockReturn(data, false, 'Timeout pobierania');
    render(<DashboardView />);
    expect(screen.getByText('Nie udało się odświeżyć danych.')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });
});