import styles from './StatusBar.module.css';

type ConnectionStatus = 'checking' | 'online' | 'offline';

interface StatusBarProps {
  status: ConnectionStatus;
  error: string | null;
  lastChecked: Date | null;
}

function formatDate(d: Date): string {
  return d.toLocaleString('pl-PL', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export default function StatusBar({ status, error, lastChecked }: StatusBarProps) {
  const dotClass =
    status === 'online'
      ? styles.dotOnline
      : status === 'offline'
        ? styles.dotOffline
        : styles.dotChecking;

  const labelClass =
    status === 'online'
      ? styles.labelOnline
      : status === 'offline'
        ? styles.labelOffline
        : styles.labelChecking;

  const statusText =
    status === 'online'
      ? 'API dostępne'
      : status === 'offline'
        ? 'API niedostępne'
        : 'Sprawdzanie połączenia...';

  return (
    <footer className={styles.statusBar} role="status" aria-live="polite">
      <div className={styles.statusLeft}>
        <span className={`${styles.dot} ${dotClass}`} aria-hidden="true" />
        <span className={`${styles.label} ${labelClass}`}>{statusText}</span>
        {error && (
          <span className={styles.errorText} title={error}>
            {error}
          </span>
        )}
      </div>

      <div className={styles.statusRight}>
        {lastChecked && (
          <span>Ostatnia kontrola: {formatDate(lastChecked)}</span>
        )}
      </div>
    </footer>
  );
}