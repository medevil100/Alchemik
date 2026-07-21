import styles from './DashboardCard.module.css';

interface DashboardCardProps {
  title: string;
  children: React.ReactNode;
}

export default function DashboardCard({ title, children }: DashboardCardProps) {
  return (
    <section className={styles.card}>
      <h2 className={styles.title}>{title}</h2>
      <div className={styles.content}>{children}</div>
    </section>
  );
}