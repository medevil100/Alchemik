import styles from './ErrorBanner.module.css';

interface ErrorBannerProps {
  message: string;
  details?: string | null;
}

export default function ErrorBanner({ message, details }: ErrorBannerProps) {
  return (
    <div className={styles.container} role="alert" aria-live="assertive">
      <div className={styles.content}>
        <span className={styles.icon} aria-hidden="true">⚠️</span>
        <div className={styles.textWrapper}>
          <p className={styles.message}>{message}</p>
          {details && <p className={styles.details}>{details}</p>}
        </div>
      </div>
    </div>
  );
}