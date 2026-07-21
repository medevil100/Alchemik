import type { HealthResponse } from '../api/types';
import styles from './HealthView.module.css';

interface HealthViewProps {
  health: HealthResponse | null;
  loading: boolean;
  error: string | null;
}

const LABELS: Record<string, string> = {
  status: 'Stan API',
  api: 'API',
  database: 'Baza danych',
  journal_mode: 'Tryb dziennika',
  schema_version: 'Wersja schematu',
  cycle_count: 'Liczba cykli',
  event_count: 'Liczba zdarzeń',
};

const CLASS_MAP: Record<string, string> = {
  status: styles.colorOk,
  api: styles.colorInfo,
  database: styles.colorOk,
  journal_mode: styles.colorWarn,
  schema_version: styles.colorWarn,
};

export default function HealthView({ health, loading, error }: HealthViewProps) {
  const hasData = health !== null;

  const renderContent = () => {
    // Loading state — back-end hasn't responded yet, no previous data
    if (loading && !hasData) {
      return <div className={styles.loading}>Łączenie z backendem...</div>;
    }

    // No data and no loading — explicit empty state
    if (!hasData) {
      return (
        <div className={styles.emptyBox}>
          Brak danych. System oczekuje na pierwszą odpowiedź API.
        </div>
      );
    }

    // We have data — render it (loading may still be true during refresh)
    return (
      <div className={styles.monitorBox}>
        {Object.entries(health).map(([key, value]) => {
          const label = LABELS[key] ?? key;
          const extraClass = CLASS_MAP[key] ?? '';
          const displayValue =
            typeof value === 'boolean'
              ? value
                ? 'Tak'
                : 'Nie'
              : String(value);

          return (
            <div className={styles.monitorRow} key={key}>
              <span className={styles.monitorKey}>{label}:</span>
              <span className={`${styles.monitorValue} ${extraClass}`}>
                {displayValue}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.heading}>ALCHEMIK — Stan systemu</h1>
        <p className={styles.subtitle}>Monitorowanie stanu API i bazy danych</p>

        {renderContent()}

        {loading && hasData && (
          <div className={styles.loadingOverlay}>
            Odświeżanie...
          </div>
        )}

        {error && !loading && (
          <div className={styles.errorBox}>{error}</div>
        )}
      </div>
    </div>
  );
}