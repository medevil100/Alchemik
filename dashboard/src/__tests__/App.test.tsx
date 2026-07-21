import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';

const { useApiHealthMock, useDashboardMock, useMarketEventsMock } = vi.hoisted(() => ({
  useApiHealthMock: vi.fn(),
  useDashboardMock: vi.fn(),
  useMarketEventsMock: vi.fn(),
}));

vi.mock('../hooks/useApiHealth', () => ({
  useApiHealth: useApiHealthMock,
}));

vi.mock('../hooks/useDashboard', () => ({
  useDashboard: useDashboardMock,
}));

vi.mock('../hooks/useMarketEvents', () => ({
  useMarketEvents: useMarketEventsMock,
}));

function mockApiHealthOnline() {
  useApiHealthMock.mockReturnValue({
    status: 'online',
    health: {
      status: 'ok',
      api: 'running',
      database: 'available',
      journal_mode: 'wal',
      schema_version: 1,
      cycle_count: 42,
      event_count: 156,
    },
    error: null,
    lastChecked: new Date(),
    loading: false,
    _checkForTest: vi.fn(),
  });
}

function mockDashboardSuccess() {
  useDashboardMock.mockReturnValue({
    data: {
      generated_at: '2026-07-21T18:00:00+00:00',
      system: {
        status: 'ok',
        database: 'available',
        journal_mode: 'wal',
        schema_version: 1,
      },
      runtime: {
        cycle_count: 1,
        event_count: 3,
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
        last_cycle_at: null,
        last_cycle_error_count: null,
        is_empty: false,
      },
      recent_activity: {
        events_in_last_cycle: 1,
        events_last_24h: 3,
        unique_tickers_last_24h: 2,
        last_event_at: '2026-07-21T17:49:10',
      },
      top_tickers: [],
      event_breakdown: {
        by_event_family: [],
        by_event_type: [],
        by_priority: [],
      },
      latest_events: [],
    },
    loading: false,
    error: null,
    lastUpdated: new Date(),
    _checkForTest: vi.fn(),
  });
}

function mockMarketEventsSuccess() {
  useMarketEventsMock.mockReturnValue({
    data: {
      items: [
        {
          event_id: 'evt-1',
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
        },
      ],
      limit: 50,
      offset: 0,
      returned: 1,
    },
    loading: false,
    error: null,
    lastUpdated: new Date(),
    setParams: vi.fn(),
    loadMore: vi.fn(),
  });
}

describe('App integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiHealthOnline();
  });

  it('domyślnie wyświetla HealthView (Stan systemu)', () => {
    render(<App />);
    // HealthView istnieje jako widok z nagłówkiem h1
    const h1 = screen.getByRole('heading', { level: 1 });
    expect(h1.textContent).toContain('Stan systemu');

    // Navigation zawiera obie pozycje
    expect(screen.getByLabelText('Pulpit')).toBeInTheDocument();
    expect(screen.getByLabelText('Stan systemu')).toBeInTheDocument();
  });

  it('przełącza na DashboardView po kliknięciu Pulpit', () => {
    mockDashboardSuccess();
    render(<App />);

    fireEvent.click(screen.getByLabelText('Pulpit'));

    // DashboardView jest widoczny — h1 to "Pulpit"
    const h1 = screen.getByRole('heading', { level: 1 });
    expect(h1.textContent).toContain('Pulpit');
    // Karty dashboardu (h2) są widoczne
    expect(screen.getAllByRole('heading', { level: 2 }).length).toBeGreaterThanOrEqual(7);
    expect(screen.getByText('System')).toBeInTheDocument();
    expect(screen.getByText('Runtime')).toBeInTheDocument();
  });

  it('wraca do HealthView po kliknięciu Stan systemu', () => {
    mockDashboardSuccess();
    render(<App />);

    // Przejdź na Pulpit
    fireEvent.click(screen.getByLabelText('Pulpit'));
    let h1 = screen.getByRole('heading', { level: 1 });
    expect(h1.textContent).toContain('Pulpit');

    // Wróć na Stan systemu
    fireEvent.click(screen.getByLabelText('Stan systemu'));
    h1 = screen.getByRole('heading', { level: 1 });
    expect(h1.textContent).toContain('Stan systemu');
  });

  it('Navigation podświetla aktywny widok', () => {
    mockDashboardSuccess();
    render(<App />);

    // Domyślnie: Stan systemu aktywny
    expect(screen.getByLabelText('Stan systemu').getAttribute('aria-current')).toBe('page');
    expect(screen.getByLabelText('Pulpit').getAttribute('aria-current')).toBeNull();

    // Po kliknięciu Pulpit
    fireEvent.click(screen.getByLabelText('Pulpit'));
    expect(screen.getByLabelText('Pulpit').getAttribute('aria-current')).toBe('page');
    expect(screen.getByLabelText('Stan systemu').getAttribute('aria-current')).toBeNull();
  });

  it('przełącza na MarketEventsView po kliknięciu Zdarzenia rynku', () => {
    mockMarketEventsSuccess();
    render(<App />);

    fireEvent.click(screen.getByLabelText('Zdarzenia rynku'));

    // MarketEventsView jest widoczny — h1 to "Zdarzenia rynku"
    const h1 = screen.getByRole('heading', { level: 1 });
    expect(h1.textContent).toContain('Zdarzenia rynku');
    // Tabela z danymi jest widoczna
    expect(
      screen.getByRole('table', { name: 'Zdarzenia rynkowe' }),
    ).toBeInTheDocument();
    expect(screen.queryAllByText('XYZ.WA').length).toBeGreaterThanOrEqual(1);
  });

  it('wraca do HealthView po przejściu ze Zdarzenia rynku', () => {
    mockMarketEventsSuccess();
    render(<App />);

    // Przejdź na Zdarzenia rynku
    fireEvent.click(screen.getByLabelText('Zdarzenia rynku'));
    let h1 = screen.getByRole('heading', { level: 1 });
    expect(h1.textContent).toContain('Zdarzenia rynku');

    // Wróć na Stan systemu
    fireEvent.click(screen.getByLabelText('Stan systemu'));
    h1 = screen.getByRole('heading', { level: 1 });
    expect(h1.textContent).toContain('Stan systemu');
  });

  it('Navigation zawiera pozycję Zdarzenia rynku z aria-current', () => {
    mockMarketEventsSuccess();
    render(<App />);

    expect(screen.getByLabelText('Zdarzenia rynku')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Zdarzenia rynku'));
    expect(
      screen.getByLabelText('Zdarzenia rynku').getAttribute('aria-current'),
    ).toBe('page');
    expect(screen.getByLabelText('Pulpit').getAttribute('aria-current')).toBeNull();
    expect(screen.getByLabelText('Stan systemu').getAttribute('aria-current')).toBeNull();
  });
});
