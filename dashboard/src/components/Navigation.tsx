import styles from './Navigation.module.css';

export type AppView = 'system-status' | 'dashboard' | 'market-events';

export interface NavItem {
  id: AppView;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Pulpit', icon: '📊' },
  { id: 'market-events', label: 'Zdarzenia rynku', icon: '📋' },
  { id: 'system-status', label: 'Stan systemu', icon: '💚' },
];

interface NavigationProps {
  activeView: AppView;
  onNavigate: (view: AppView) => void;
}

export default function Navigation({ activeView, onNavigate }: NavigationProps) {
  return (
    <nav className={styles.nav} role="navigation" aria-label="Główna nawigacja">
      <div className={styles.brand}>
        <span className={styles.brandIcon}>🧪</span>
        <span>ALCHEMIK</span>
      </div>

      <ul className={styles.navList}>
        {NAV_ITEMS.map((item) => (
          <li key={item.id}>
            <button
              className={`${styles.navItem} ${activeView === item.id ? styles.navItemActive : ''}`}
              aria-current={activeView === item.id ? 'page' : undefined}
              aria-label={item.label}
              onClick={() => onNavigate(item.id)}
              type="button"
            >
              <span className={styles.navIcon}>{item.icon}</span>
              <span className={styles.navLabel}>{item.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
