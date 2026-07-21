import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatusBar from '../StatusBar';

describe('StatusBar', () => {
  const lastChecked = new Date('2026-07-21T12:00:00Z');

  it('renders API available status', () => {
    render(<StatusBar status="online" error={null} lastChecked={lastChecked} />);
    expect(screen.getByText(/API dostępne/)).toBeInTheDocument();
    expect(screen.getByText(/Ostatnia kontrola/)).toBeInTheDocument();
  });

  it('renders API unavailable status with error', () => {
    render(<StatusBar status="offline" error="Connection refused" lastChecked={lastChecked} />);
    expect(screen.getByText(/API niedostępne/)).toBeInTheDocument();
    expect(screen.getByText('Connection refused')).toBeInTheDocument();
  });

  it('renders checking status', () => {
    render(<StatusBar status="checking" error={null} lastChecked={null} />);
    expect(screen.getByText(/Sprawdzanie połączenia/)).toBeInTheDocument();
  });

  it('shows last checked time', () => {
    render(<StatusBar status="online" error={null} lastChecked={lastChecked} />);
    expect(screen.getByText(/Ostatnia kontrola/)).toBeInTheDocument();
  });

  it('does NOT render a manual refresh button', () => {
    render(<StatusBar status="online" error={null} lastChecked={lastChecked} />);
    expect(screen.queryByText('Odśwież')).not.toBeInTheDocument();
  });
});