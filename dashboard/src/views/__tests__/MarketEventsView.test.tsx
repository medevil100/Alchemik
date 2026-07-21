import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import MarketEventsView from '../MarketEventsView';
import type { PaginatedResponse, MarketEvent } from '../../api/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

let mockData: PaginatedResponse<MarketEvent>;
let mockLoading: boolean;
let mockError: string | null;
const setParamsMock = vi.fn();
const loadMoreMock = vi.fn();

const { useMarketEventsMock } = vi.hoisted(() => ({
  useMarketEventsMock: vi.fn(),
}));

vi.mock('../../hooks/useMarketEvents', () => ({
  useMarketEvents: useMarketEventsMock,
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

function mockSuccess(items: MarketEvent[] = [buildEvent()]) {
  mockData = buildResponse(items);
  mockLoading = false;
  mockError = null;
  useMarketEventsMock.mockReturnValue({
    data: mockData,
    loading: mockLoading,
    error: mockError,
    lastUpdated: new Date(),
    setParams: setParamsMock,
    loadMore: loadMoreMock,
  });
}

function mockLoadingState() {
  useMarketEventsMock.mockReturnValue({
    data: null,
    loading: true,
    error: null,
    lastUpdated: null,
    setParams: setParamsMock,
    loadMore: loadMoreMock,
  });
}

function mockErrorState() {
  useMarketEventsMock.mockReturnValue({
    data: null,
    loading: false,
    error: 'Backend niedostępny',
    lastUpdated: null,
    setParams: setParamsMock,
    loadMore: loadMoreMock,
  });
}

function mockEmpty() {
  mockData = buildResponse([], { returned: 0 });
  mockLoading = false;
  mockError = null;
  useMarketEventsMock.mockReturnValue({
    data: mockData,
    loading: false,
    error: null,
    lastUpdated: new Date(),
    setParams: setParamsMock,
    loadMore: loadMoreMock,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MarketEventsView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- States ---

  it('wyświetla LoadingSpinner podczas pierwszego ładowania', () => {
    mockLoadingState();
    render(<MarketEventsView />);
    expect(screen.getByText('Ładowanie zdarzeń rynku…')).toBeInTheDocument();
  });

  it('wyświetla ErrorBanner gdy błąd pierwszego pobrania', () => {
    mockErrorState();
    render(<MarketEventsView />);
    expect(
      screen.getByText('Nie udało się załadować listy zdarzeń rynku.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Backend niedostępny')).toBeInTheDocument();
  });

  it('wyświetla EmptyState gdy brak zdarzeń na pierwszej stronie', () => {
    mockEmpty();
    render(<MarketEventsView />);
    expect(screen.getByText('Brak zdarzeń rynkowych')).toBeInTheDocument();
  });

  it('wyświetla tabelę z danymi po pomyślnym pobraniu', () => {
    mockSuccess();
    render(<MarketEventsView />);

    expect(
      screen.getByRole('heading', { level: 1, name: 'Zdarzenia rynku' }),
    ).toBeInTheDocument();

    const table = screen.getByRole('table', {
      name: 'Zdarzenia rynkowe',
    });
    expect(table).toBeInTheDocument();

    expect(within(table).getByText('Czas (UTC)')).toBeInTheDocument();
    expect(within(table).getByText('Ticker')).toBeInTheDocument();
    expect(within(table).getByText('Rynek')).toBeInTheDocument();
    expect(within(table).getByText('Rodzina')).toBeInTheDocument();
    expect(within(table).getByText('Typ')).toBeInTheDocument();
    expect(within(table).getByText('Priorytet')).toBeInTheDocument();
    expect(within(table).getByText('Pewność')).toBeInTheDocument();

    expect(screen.queryAllByText('XYZ.WA').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('GPW').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('PRICE').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('PRICE_SURGE').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('Krytyczny (CRITICAL)').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('85%').length).toBeGreaterThanOrEqual(1);
  });

  // --- Multiple records ---

  it('wyświetla wiele rekordów', () => {
    mockSuccess([
      buildEvent({ event_id: '1', ticker: 'AAA.WA' }),
      buildEvent({ event_id: '2', ticker: 'BBB.WA' }),
      buildEvent({ event_id: '3', ticker: 'CCC.WA' }),
    ]);
    render(<MarketEventsView />);
    expect(screen.queryAllByText('AAA.WA').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('BBB.WA').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('CCC.WA').length).toBeGreaterThanOrEqual(1);
  });

  // --- Missing fields ---

  it('obsługuje brakujące pola', () => {
    mockSuccess([
      buildEvent({
        event_id: 'minimal',
        market: undefined as unknown as string,
        event_type: undefined as unknown as string,
        confidence_level: undefined as unknown as number,
      }),
    ]);
    render(<MarketEventsView />);
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  // --- Priority format ---

  it('wyświetla priorytet w formacie Tłumaczenie (WARTOŚĆ)', () => {
    mockSuccess([
      buildEvent({ event_id: 'p1', priority_final: 'CRITICAL' }),
      buildEvent({ event_id: 'p2', priority_final: 'HIGH' }),
      buildEvent({ event_id: 'p3', priority_final: 'MEDIUM' }),
      buildEvent({ event_id: 'p4', priority_final: 'LOW' }),
      buildEvent({ event_id: 'p5', priority_final: 'IGNORE' }),
    ]);
    render(<MarketEventsView />);
    expect(screen.queryAllByText('Krytyczny (CRITICAL)').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('Wysoki (HIGH)').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('Średni (MEDIUM)').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('Niski (LOW)').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('Ignorowany (IGNORE)').length).toBeGreaterThanOrEqual(1);
  });

  it('wyświetla nieznany priorytet jako surowy tekst', () => {
    mockSuccess([
      buildEvent({ event_id: 'unknown', priority_final: 'UNKNOWN_PRIO' }),
    ]);
    render(<MarketEventsView />);
    expect(screen.queryAllByText('UNKNOWN_PRIO').length).toBeGreaterThanOrEqual(1);
  });

  // --- Confidence format ---

  it('formatuje confidence_level 0–1 jako procent', () => {
    mockSuccess([buildEvent({ event_id: 'c1', confidence_level: 0.85 })]);
    render(<MarketEventsView />);
    expect(screen.queryAllByText('85%').length).toBeGreaterThanOrEqual(1);
  });

  it('obsługuje confidence_level null/undefined/NaN jako —', () => {
    mockSuccess([
      buildEvent({
        event_id: 'c-null',
        confidence_level: undefined as unknown as number,
      }),
    ]);
    render(<MarketEventsView />);
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  // --- Filters ---

  it('renderuje formularz filtrów', () => {
    mockSuccess();
    render(<MarketEventsView />);
    expect(screen.getByLabelText('Filtry zdarzeń rynkowych')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Zastosuj filtry' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Wyczyść filtry' })).toBeInTheDocument();
  });

  it('wywołuje setParams po zastosowaniu filtrów', () => {
    mockSuccess();
    render(<MarketEventsView />);

    const tickerInput = screen.getByPlaceholderText('np. XYZ.WA');
    fireEvent.change(tickerInput, { target: { value: 'ABC.WA' } });

    fireEvent.click(screen.getByRole('button', { name: 'Zastosuj filtry' }));
    expect(setParamsMock).toHaveBeenCalledWith(
      expect.objectContaining({ ticker: 'ABC.WA', offset: 0 }),
    );
  });

  it('czyści filtry po kliknięciu Wyczyść filtry', () => {
    mockSuccess();
    render(<MarketEventsView />);

    const tickerInput = screen.getByPlaceholderText('np. XYZ.WA');
    fireEvent.change(tickerInput, { target: { value: 'ABC.WA' } });

    fireEvent.click(screen.getByRole('button', { name: 'Wyczyść filtry' }));
    expect(setParamsMock).toHaveBeenCalledWith(
      expect.objectContaining({ offset: 0, limit: 50 }),
    );
  });

  // --- Date fields convert YYYY-MM-DD to ISO 8601 ---

  it('konwertuje date_from do ISO 8601 granicy dnia', () => {
    mockSuccess();
    render(<MarketEventsView />);

    const dateFrom = screen.getByLabelText('Data od');
    fireEvent.change(dateFrom, { target: { value: '2026-01-15' } });

    fireEvent.click(screen.getByRole('button', { name: 'Zastosuj filtry' }));
    expect(setParamsMock).toHaveBeenCalledWith(
      expect.objectContaining({ date_from: '2026-01-15T00:00:00', offset: 0 }),
    );
  });

  it('konwertuje date_to do ISO 8601 z mikrosekundami', () => {
    mockSuccess();
    render(<MarketEventsView />);

    const dateTo = screen.getByLabelText('Data do');
    fireEvent.change(dateTo, { target: { value: '2026-01-15' } });

    fireEvent.click(screen.getByRole('button', { name: 'Zastosuj filtry' }));
    expect(setParamsMock).toHaveBeenCalledWith(
      expect.objectContaining({ date_to: '2026-01-15T23:59:59.999999', offset: 0 }),
    );
  });

  // --- Pagination ---

  it('wyświetla kontrolki paginacji desktopowej', () => {
    mockSuccess(
      Array.from({ length: 50 }, (_, i) =>
        buildEvent({ event_id: String(i), ticker: `T${i}.WA` }),
      ),
    );
    render(<MarketEventsView />);
    expect(
      screen.getByRole('button', { name: '← Poprzednia' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Następna →' }),
    ).toBeInTheDocument();
  });

  it('przycisk Poprzednia jest nieaktywny na pierwszej stronie', () => {
    mockSuccess();
    render(<MarketEventsView />);
    const prev = screen.getByRole('button', { name: '← Poprzednia' });
    expect(prev).toBeDisabled();
  });

  it('przycisk Następna enabled gdy returned >= limit (może istnieć więcej)', () => {
    mockSuccess(
      Array.from({ length: 50 }, (_, i) =>
        buildEvent({ event_id: String(i), ticker: `T${i}.WA` }),
      ),
    );
    render(<MarketEventsView />);
    const next = screen.getByRole('button', { name: 'Następna →' });
    expect(next).toBeEnabled();
  });

  it('przycisk Następna disabled gdy returned < limit', () => {
    mockSuccess([buildEvent()]);
    render(<MarketEventsView />);
    const next = screen.getByRole('button', { name: 'Następna →' });
    expect(next).toBeDisabled();
  });

  it('pusta kolejna strona pokazuje komunikat i nie czyści danych', () => {
    mockData = buildResponse([], { offset: 50, returned: 0 });
    mockLoading = false;
    mockError = null;
    useMarketEventsMock.mockReturnValue({
      data: mockData,
      loading: false,
      error: null,
      lastUpdated: new Date(),
      setParams: setParamsMock,
      loadMore: loadMoreMock,
    });

    render(<MarketEventsView />);

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(
      screen.getByText('Nie ma więcej zdarzeń spełniających podane kryteria.'),
    ).toBeInTheDocument();
  });

  // --- No links/buttons for details ---

  it('nie zawiera linków ani przycisków do szczegółów', () => {
    mockSuccess();
    render(<MarketEventsView />);
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    const table = screen.getByRole('table', { name: 'Zdarzenia rynkowe' });
    const rowButtons = within(table).queryAllByRole('button');
    expect(rowButtons).toHaveLength(0);
  });

  // --- Mobile cards ---

  it('renderuje karty dla widoku mobilnego', () => {
    mockSuccess([buildEvent()]);
    render(<MarketEventsView />);
    const cards = document.querySelectorAll('article');
    expect(cards.length).toBeGreaterThanOrEqual(1);
  });

  // --- Accessibility ---

  it('posiada jeden h1', () => {
    mockSuccess();
    render(<MarketEventsView />);
    const headings = screen.getAllByRole('heading', { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0]).toHaveTextContent('Zdarzenia rynku');
  });

  it('tabela ma semantyczne th scope="col"', () => {
    mockSuccess();
    render(<MarketEventsView />);
    const table = screen.getByRole('table', { name: 'Zdarzenia rynkowe' });
    const headers = within(table).getAllByRole('columnheader');
    expect(headers.length).toBe(7);
    headers.forEach((th) => {
      expect(th).toHaveAttribute('scope', 'col');
    });
  });

  it('pagination ma aria-label', () => {
    mockSuccess(
      Array.from({ length: 50 }, (_, i) =>
        buildEvent({ event_id: String(i), ticker: `T${i}.WA` }),
      ),
    );
    render(<MarketEventsView />);
    expect(
      screen.getByRole('navigation', {
        name: 'Paginacja zdarzeń rynkowych',
      }),
    ).toBeInTheDocument();
  });

  it('status podsumowania ma aria-live polite', () => {
    mockSuccess();
    render(<MarketEventsView />);
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
  });
});