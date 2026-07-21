import styles from './EmptyState.module.css';

interface EmptyStateProps {
  title: string;
  description?: string;
}

export default function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className={styles.container} role="status" aria-live="polite">
      <span className={styles.icon} aria-hidden="true">📋</span>
      <h3 className={styles.title}>{title}</h3>
      {description && <p className={styles.description}>{description}</p>}
    </div>
  );
}