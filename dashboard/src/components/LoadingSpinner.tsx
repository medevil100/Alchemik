import styles from './LoadingSpinner.module.css';

interface LoadingSpinnerProps {
  message?: string;
}

export default function LoadingSpinner({ message = 'Ładowanie…' }: LoadingSpinnerProps) {
  return (
    <div className={styles.container} role="status" aria-live="polite">
      <div className={styles.spinner} aria-hidden="true" />
      <p className={styles.message}>{message}</p>
    </div>
  );
}