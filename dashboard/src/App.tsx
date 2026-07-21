import { useState } from 'react';
import Navigation from './components/Navigation';
import type { AppView } from './components/Navigation';
import StatusBar from './components/StatusBar';
import HealthView from './views/HealthView';
import DashboardView from './views/DashboardView';
import MarketEventsView from './views/MarketEventsView';
import { useApiHealth } from './hooks/useApiHealth';
import styles from './App.module.css';

export default function App() {
  const { status, health, error, lastChecked, loading } = useApiHealth();
  const [activeView, setActiveView] = useState<AppView>('system-status');

  return (
    <div className={styles.appContainer}>
      <div className={styles.contentWrapper}>
        <Navigation activeView={activeView} onNavigate={setActiveView} />

        <main className={styles.main}>
          {activeView === 'system-status' && (
            <HealthView
              health={health}
              loading={loading}
              error={error}
            />
          )}
          {activeView === 'dashboard' && <DashboardView />}
          {activeView === 'market-events' && <MarketEventsView />}
        </main>
      </div>

      <StatusBar
        status={status}
        error={error}
        lastChecked={lastChecked}
      />
    </div>
  );
}
