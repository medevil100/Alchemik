import { useDashboard } from '../hooks/useDashboard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import EmptyState from '../components/EmptyState';
import DashboardCard from '../components/DashboardCard';
import styles from './DashboardView.module.css';

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

function priorityLabel(priority: string): string {
  const labels: Record<string, string> = {
    CRITICAL: 'Krytyczny',
    HIGH: 'Wysoki',
    MEDIUM: 'Średni',
    LOW: 'Niski',
    IGNORE: 'Ignorowany',
  };
  return labels[priority] ?? priority;
}

export default function DashboardView() {
  const { data, loading, error } = useDashboard();

  if (loading && !data) {
    return <LoadingSpinner message="Ładowanie panelu głównego…" />;
  }

  if (error && !data) {
    return <ErrorBanner message="Nie udało się załadować panelu głównego." details={error} />;
  }

  if (!data) {
    return <ErrorBanner message="Nie udało się załadować panelu głównego." />;
  }

  const { system, runtime, recent_activity, top_tickers, event_breakdown, latest_events } = data;
  const isEmpty = runtime.is_empty;

  if (isEmpty) {
    return (
      <div className={styles.container}>
        <h1 className={styles.pageTitle}>Pulpit</h1>
        <EmptyState
          title="Brak danych"
          description="System oczekuje na pierwszy cykl Runtime. To może potrwać do 15 minut od uruchomienia."
        />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.pageTitle}>Pulpit</h1>
        {error && <ErrorBanner message="Nie udało się odświeżyć danych." details={error} />}
      </div>

      <div className={styles.grid}>
        <DashboardCard title="System">
          <dl className={styles.definitionList}>
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Stan API</dt>
              <dd className={styles.definition}>
                <span className={system.status === 'ok' ? styles.badgeOk : styles.badgeError}>
                  {system.status === 'ok' ? 'online' : system.status}
                </span>
              </dd>
            </div>
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Baza danych</dt>
              <dd className={styles.definition}>{system.database}</dd>
            </div>
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Tryb dziennika</dt>
              <dd className={styles.definition}>{system.journal_mode}</dd>
            </div>
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Wersja schematu</dt>
              <dd className={styles.definition}>{system.schema_version}</dd>
            </div>
          </dl>
        </DashboardCard>

        <DashboardCard title="Runtime">
          <dl className={styles.definitionList}>
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Liczba cykli</dt>
              <dd className={styles.definition}>{runtime.cycle_count.toLocaleString('pl-PL')}</dd>
            </div>
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Liczba zdarzeń</dt>
              <dd className={styles.definition}>{runtime.event_count.toLocaleString('pl-PL')}</dd>
            </div>
            {runtime.last_cycle && (
              <div className={styles.definitionRow}>
                <dt className={styles.term}>Ostatni cykl</dt>
                <dd className={styles.definition}>
                  <span className={runtime.last_cycle.status === 'completed' ? styles.badgeOk : styles.badgeError}>
                    {runtime.last_cycle.status}
                  </span>{' '}
                  — {formatDateTime(runtime.last_cycle.created_at)}
                </dd>
              </div>
            )}
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Błędy w ostatnim cyklu</dt>
              <dd className={styles.definition}>
                {runtime.last_cycle_error_count !== null ? runtime.last_cycle_error_count : '—'}
              </dd>
            </div>
          </dl>
        </DashboardCard>

        <DashboardCard title="Ostatnia aktywność">
          <dl className={styles.definitionList}>
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Zdarzenia w ostatnim cyklu</dt>
              <dd className={styles.definition}>{recent_activity.events_in_last_cycle}</dd>
            </div>
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Zdarzenia w ciągu ostatnich 24 h</dt>
              <dd className={styles.definition}>{recent_activity.events_last_24h}</dd>
            </div>
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Unikalne tickery (24 h)</dt>
              <dd className={styles.definition}>{recent_activity.unique_tickers_last_24h}</dd>
            </div>
            <div className={styles.definitionRow}>
              <dt className={styles.term}>Ostatnie zdarzenie</dt>
              <dd className={styles.definition}>{formatDateTime(recent_activity.last_event_at)}</dd>
            </div>
          </dl>
        </DashboardCard>

        <DashboardCard title="Najaktywniejsze tickery">
          {top_tickers.length === 0 ? (
            <p className={styles.emptyText}>Brak tickerów w wybranym oknie czasowym.</p>
          ) : (
            <div className={styles.scrollableTable}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Liczba zdarzeń</th>
                    <th>Priorytet</th>
                    <th>Ostatnie zdarzenie</th>
                  </tr>
                </thead>
                <tbody>
                  {top_tickers.map((t) => (
                    <tr key={t.ticker}>
                      <td className={styles.tickerCell}>{t.ticker}</td>
                      <td>{t.event_count}</td>
                      <td>{priorityLabel(t.priority_final)}</td>
                      <td>{formatDateTime(t.last_event_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DashboardCard>

        <DashboardCard title="Podział zdarzeń wg rodziny">
          {event_breakdown.by_event_family.length === 0 ? (
            <p className={styles.emptyText}>Brak danych.</p>
          ) : (
            <ul className={styles.breakdownList}>
              {event_breakdown.by_event_family.map((item) => (
                <li key={item.event_family} className={styles.breakdownItem}>
                  <span className={styles.breakdownKey}>{item.event_family ?? item.key ?? '—'}</span>
                  <span className={styles.breakdownValue}>{item.count}</span>
                </li>
              ))}
            </ul>
          )}
        </DashboardCard>

        <DashboardCard title="Podział zdarzeń wg priorytetu">
          {event_breakdown.by_priority.length === 0 ? (
            <p className={styles.emptyText}>Brak danych.</p>
          ) : (
            <ul className={styles.breakdownList}>
              {event_breakdown.by_priority.map((item) => (
                <li key={item.priority} className={styles.breakdownItem}>
                  <span className={styles.breakdownKey}>{priorityLabel(item.priority ?? item.key ?? '—')}</span>
                  <span className={styles.breakdownValue}>{item.count}</span>
                </li>
              ))}
            </ul>
          )}
        </DashboardCard>

        <DashboardCard title="Najnowsze zdarzenia">
          {latest_events.length === 0 ? (
            <p className={styles.emptyText}>Brak zdarzeń w wybranym oknie czasowym.</p>
          ) : (
            <div className={styles.scrollableTable}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Czas (UTC)</th>
                    <th>Ticker</th>
                    <th>Rodzina</th>
                    <th>Typ</th>
                    <th>Priorytet</th>
                  </tr>
                </thead>
                <tbody>
                  {latest_events.map((event) => (
                    <tr key={event.event_id}>
                      <td>{formatDateTime(event.timestamp_utc)}</td>
                      <td className={styles.tickerCell}>{event.ticker}</td>
                      <td>{event.event_family}</td>
                      <td className={styles.monoText}>{event.event_type}</td>
                      <td>{priorityLabel(event.priority_final)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DashboardCard>
      </div>
    </div>
  );
}