import { useState, useCallback } from 'react';
import { useMarketEvents } from '../hooks/useMarketEvents';
import type { EventListParams } from '../api/api';
import { API_CONFIG } from '../api/config';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import EmptyState from '../components/EmptyState';
import styles from './MarketEventsView.module.css';

// ---------------------------------------------------------------------------
// Constants — based on docs/Kontrakt_Zdarzen_Rynkowych.md
// ---------------------------------------------------------------------------

/**
 * Event families as defined in the contract (docs/Hierarchia_Zdarzen_Rynkowych.md).
 * Kept as a local constant; source of truth remains the backend enum.
 */
const EVENT_FAMILIES: string[] = [
  'PRICE',
  'VOLUME',
  'TECHNICAL',
  'FUNDAMENTAL',
  'CORPORATE',
  'REGULATORY',
  'MACRO',
  'ETF',
  'DERIVATIVES',
  'SENTIMENT',
  'SYSTEM',
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pl-PL', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

/**
 * Map priority_final technical values to display labels.
 * Contract values: CRITICAL, HIGH, MEDIUM, LOW, IGNORE.
 * No official Polish translations exist in the docs, so we show
 * both the translation AND the technical value for clarity.
 */
function formatPriority(priority: string | null | undefined): string {
  if (!priority) return '—';
  const labels: Record<string, string> = {
    CRITICAL: 'Krytyczny',
    HIGH: 'Wysoki',
    MEDIUM: 'Średni',
    LOW: 'Niski',
    IGNORE: 'Ignorowany',
  };
  const translated = labels[priority];
  if (translated) {
    return `${translated} (${priority})`;
  }
  // Unknown value — return as-is, never throw.
  return priority;
}

/**
 * Format confidence_level (0.0–1.0 per Kontrakt_Zdarzen_Rynkowych.md, field 12).
 * Handles null, undefined, NaN, and values outside the documented range.
 */
function formatConfidence(level: number | null | undefined): string {
  if (level == null) return '—';
  if (typeof level !== 'number' || Number.isNaN(level)) return '—';
  // Contract says 0.0–1.0.
  return `${Math.round(level * 100)}%`;
}

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------

interface Filters {
  ticker: string;
  event_family: string;
  event_type: string;
  priority_final: string;
  date_from: string;
  date_to: string;
}

/**
 * Build API params from local filter state.
 * For date fields we extend YYYY-MM-DD to ISO 8601 boundaries.
 * date_to uses 23:59:59.999999 to include events with microsecond timestamps.
 * Backend uses SQLite text comparison (lexicographic), so 'T23:59:59.999999'
 * catches all events up to and including 23:59:59.999999 of the selected day.
 */
function buildApiParams(filters: Filters, offset: number): EventListParams {
  const params: EventListParams = {
    limit: API_CONFIG.DEFAULT_PAGE_LIMIT,
    offset,
  };
  if (filters.ticker.trim()) params.ticker = filters.ticker.trim();
  if (filters.event_family) params.event_family = filters.event_family;
  if (filters.event_type.trim()) params.event_type = filters.event_type.trim();
  if (filters.priority_final) params.priority_final = filters.priority_final;
  if (filters.date_from) params.date_from = `${filters.date_from}T00:00:00`;
  if (filters.date_to) params.date_to = `${filters.date_to}T23:59:59.999999`;
  return params;
}

const EMPTY_FILTERS: Filters = {
  ticker: '',
  event_family: '',
  event_type: '',
  priority_final: '',
  date_from: '',
  date_to: '',
};

// ---------------------------------------------------------------------------
// View
// ---------------------------------------------------------------------------

export default function MarketEventsView() {
  const { data, loading, error, setParams, loadMore } = useMarketEvents({
    limit: API_CONFIG.DEFAULT_PAGE_LIMIT,
    offset: 0,
  });

  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [offset, setOffset] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  // Track whether "Load more" is exhausted
  const [moreExhausted, setMoreExhausted] = useState(false);

  const applyFilters = useCallback(
    (newFilters: Filters, newOffset = 0) => {
      setOffset(newOffset);
      setMoreExhausted(false);
      setParams(buildApiParams(newFilters, newOffset));
    },
    [setParams],
  );

  const handleFilterChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    applyFilters(filters, 0);
  };

  const handleClearFilters = () => {
    setFilters(EMPTY_FILTERS);
    applyFilters(EMPTY_FILTERS, 0);
  };

  const handlePrevPage = () => {
    const newOffset = Math.max(0, offset - API_CONFIG.DEFAULT_PAGE_LIMIT);
    applyFilters(filters, newOffset);
  };

  const handleNextPage = () => {
    const newOffset = offset + API_CONFIG.DEFAULT_PAGE_LIMIT;
    applyFilters(filters, newOffset);
  };

  const handleLoadMore = () => {
    const nextOffset = offset + API_CONFIG.DEFAULT_PAGE_LIMIT;
    setOffset(nextOffset);
    // Use loadMore which accumulates items
    loadMore(nextOffset);
  };

  // --- States ---

  // Loading on first fetch
  if (loading && !data) {
    return <LoadingSpinner message="Ładowanie zdarzeń rynku…" />;
  }

  // Error on first fetch (no data at all)
  if (error && !data) {
    return (
      <ErrorBanner
        message="Nie udało się załadować listy zdarzeń rynku."
        details={error}
      />
    );
  }

  if (!data) {
    return (
      <ErrorBanner message="Nie udało się załadować listy zdarzeń rynku." />
    );
  }

  const events = data.items;
  // hasMore = API returned a full page → there MAY be more, not guaranteed.
  const hasMore = data.returned >= API_CONFIG.DEFAULT_PAGE_LIMIT && !moreExhausted;
  const isFirstPage = data.offset === 0;
  const isEmpty = events.length === 0 && !error;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.pageTitle}>Zdarzenia rynku</h1>
        {error && (
          <ErrorBanner
            message="Nie udało się odświeżyć danych."
            details={error}
          />
        )}
      </header>

      {/* Filter bar */}
      <div className={styles.filterBarContainer}>
        <button
          className={styles.filterToggle}
          type="button"
          aria-expanded={filtersOpen}
          aria-controls="market-events-filters"
          onClick={() => setFiltersOpen((o) => !o)}
        >
          {filtersOpen ? 'Ukryj filtry ▲' : 'Pokaż filtry ▼'}
        </button>

        <form
          id="market-events-filters"
          className={`${styles.filterForm} ${filtersOpen ? styles.filterFormOpen : ''}`}
          onSubmit={handleFilterSubmit}
          aria-label="Filtry zdarzeń rynkowych"
        >
          <div className={styles.filterGrid}>
            <label className={styles.filterField}>
              <span className={styles.filterLabel}>Ticker</span>
              <input
                className={styles.filterInput}
                type="text"
                name="ticker"
                value={filters.ticker}
                onChange={handleFilterChange}
                placeholder="np. XYZ.WA"
              />
            </label>

            <label className={styles.filterField}>
              <span className={styles.filterLabel}>Rodzina zdarzeń</span>
              <select
                className={styles.filterInput}
                name="event_family"
                value={filters.event_family}
                onChange={handleFilterChange}
              >
                <option value="">Wszystkie</option>
                {EVENT_FAMILIES.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.filterField}>
              <span className={styles.filterLabel}>Typ zdarzenia</span>
              <input
                className={styles.filterInput}
                type="text"
                name="event_type"
                value={filters.event_type}
                onChange={handleFilterChange}
                placeholder="np. PRICE_SURGE"
              />
            </label>

            <label className={styles.filterField}>
              <span className={styles.filterLabel}>Priorytet</span>
              <select
                className={styles.filterInput}
                name="priority_final"
                value={filters.priority_final}
                onChange={handleFilterChange}
              >
                <option value="">Wszystkie</option>
                <option value="CRITICAL">Krytyczny (CRITICAL)</option>
                <option value="HIGH">Wysoki (HIGH)</option>
                <option value="MEDIUM">Średni (MEDIUM)</option>
                <option value="LOW">Niski (LOW)</option>
                <option value="IGNORE">Ignorowany (IGNORE)</option>
              </select>
            </label>

            <label className={styles.filterField}>
              <span className={styles.filterLabel}>Data od</span>
              <input
                className={styles.filterInput}
                type="date"
                name="date_from"
                value={filters.date_from}
                onChange={handleFilterChange}
              />
            </label>

            <label className={styles.filterField}>
              <span className={styles.filterLabel}>Data do</span>
              <input
                className={styles.filterInput}
                type="date"
                name="date_to"
                value={filters.date_to}
                onChange={handleFilterChange}
              />
            </label>
          </div>

          <div className={styles.filterActions}>
            <button className={styles.filterApply} type="submit">
              Zastosuj filtry
            </button>
            <button
              className={styles.filterClear}
              type="button"
              onClick={handleClearFilters}
            >
              Wyczyść filtry
            </button>
          </div>
        </form>
      </div>

      {/* Summary */}
      <p className={styles.summary} role="status" aria-live="polite">
        Wyświetlono {data.returned} zdarzeń (strona {Math.floor(offset / API_CONFIG.DEFAULT_PAGE_LIMIT) + 1})
      </p>

      {/* Empty state — only on first page */}
      {isEmpty && isFirstPage && (
        <EmptyState
          title="Brak zdarzeń rynkowych"
          description="Brak zdarzeń spełniających podane kryteria."
        />
      )}

      {/* Empty state — beyond first page means no more data */}
      {isEmpty && !isFirstPage && (
        <div className={styles.noMoreContainer}>
          <p className={styles.noMoreText}>
            Nie ma więcej zdarzeń spełniających podane kryteria.
          </p>
        </div>
      )}

      {/* Desktop table */}
      {!isEmpty && (
        <div className={styles.tableContainer}>
          <table className={styles.table} aria-label="Zdarzenia rynkowe">
            <thead>
              <tr>
                <th scope="col">Czas (UTC)</th>
                <th scope="col">Ticker</th>
                <th scope="col">Rynek</th>
                <th scope="col">Rodzina</th>
                <th scope="col">Typ</th>
                <th scope="col">Priorytet</th>
                <th scope="col">Pewność</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.event_id}>
                  <td>{formatDateTime(event.timestamp_utc)}</td>
                  <td className={styles.tickerCell}>{event.ticker}</td>
                  <td>{event.market ?? '—'}</td>
                  <td>{event.event_family ?? '—'}</td>
                  <td className={styles.monoText}>{event.event_type ?? '—'}</td>
                  <td>{formatPriority(event.priority_final)}</td>
                  <td className={styles.monoText}>
                    {formatConfidence(event.confidence_level)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Mobile cards */}
      {!isEmpty && (
        <div className={styles.cardList}>
          {events.map((event) => (
            <article key={event.event_id} className={styles.eventCard}>
              <h2 className={styles.cardTicker}>{event.ticker}</h2>
              <dl className={styles.cardDetails}>
                <div className={styles.cardRow}>
                  <dt>Czas</dt>
                  <dd>{formatDateTime(event.timestamp_utc)}</dd>
                </div>
                <div className={styles.cardRow}>
                  <dt>Rynek</dt>
                  <dd>{event.market ?? '—'}</dd>
                </div>
                <div className={styles.cardRow}>
                  <dt>Rodzina</dt>
                  <dd>{event.event_family ?? '—'}</dd>
                </div>
                <div className={styles.cardRow}>
                  <dt>Typ</dt>
                  <dd>{event.event_type ?? '—'}</dd>
                </div>
                <div className={styles.cardRow}>
                  <dt>Priorytet</dt>
                  <dd>{formatPriority(event.priority_final)}</dd>
                </div>
                <div className={styles.cardRow}>
                  <dt>Pewność</dt>
                  <dd>{formatConfidence(event.confidence_level)}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isEmpty && (
        <nav className={styles.pagination} aria-label="Paginacja zdarzeń rynkowych">
          <div className={styles.paginationDesktop}>
            <button
              className={styles.paginationButton}
              onClick={handlePrevPage}
              disabled={offset === 0}
              type="button"
            >
              ← Poprzednia
            </button>
            <span className={styles.paginationInfo}>
              Strona {Math.floor(offset / API_CONFIG.DEFAULT_PAGE_LIMIT) + 1}
            </span>
            <button
              className={styles.paginationButton}
              onClick={handleNextPage}
              disabled={!hasMore}
              type="button"
            >
              Następna →
            </button>
          </div>

          {/* Mobile "load more" — accumulates items, not pages */}
          {hasMore && (
            <div className={styles.paginationMobile}>
              <button
                className={styles.loadMoreButton}
                onClick={handleLoadMore}
                type="button"
              >
                Załaduj więcej
              </button>
            </div>
          )}
        </nav>
      )}
    </div>
  );
}