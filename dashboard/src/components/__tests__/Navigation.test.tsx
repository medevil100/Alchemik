import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Navigation from '../Navigation';

function renderNav(activeView: 'system-status' | 'dashboard' | 'market-events' = 'system-status') {
  const onNavigate = vi.fn();
  const utils = render(
    <Navigation activeView={activeView} onNavigate={onNavigate} />,
  );
  return { ...utils, onNavigate };
}

describe('Navigation', () => {
  it('renders brand name', () => {
    renderNav();
    expect(screen.getByText('ALCHEMIK')).toBeInTheDocument();
  });

  it('renders all nav items: Pulpit, Zdarzenia rynku, and Stan systemu', () => {
    renderNav();
    expect(screen.getByText('Pulpit')).toBeInTheDocument();
    expect(screen.getByText('Zdarzenia rynku')).toBeInTheDocument();
    expect(screen.getByText('Stan systemu')).toBeInTheDocument();
    expect(screen.getByLabelText('Pulpit')).toBeInTheDocument();
    expect(screen.getByLabelText('Zdarzenia rynku')).toBeInTheDocument();
    expect(screen.getByLabelText('Stan systemu')).toBeInTheDocument();
  });

  it('does not render any future business nav items', () => {
    renderNav();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Market Events')).not.toBeInTheDocument();
    expect(screen.queryByText('Cycles')).not.toBeInTheDocument();
    expect(screen.queryByText('Runtime Status')).not.toBeInTheDocument();
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
  });

  it('has aria-current on the active button (Stan systemu)', () => {
    renderNav('system-status');
    const buttons = screen.getAllByRole('button');
    const stanSystemu = buttons.find((b) => b.getAttribute('aria-label') === 'Stan systemu');
    expect(stanSystemu).toBeDefined();
    expect(stanSystemu!.getAttribute('aria-current')).toBe('page');

    const pulpit = buttons.find((b) => b.getAttribute('aria-label') === 'Pulpit');
    expect(pulpit).toBeDefined();
    expect(pulpit!.getAttribute('aria-current')).toBeNull();
  });

  it('has aria-current on the active button (Pulpit)', () => {
    renderNav('dashboard');
    const buttons = screen.getAllByRole('button');
    const pulpit = buttons.find((b) => b.getAttribute('aria-label') === 'Pulpit');
    expect(pulpit).toBeDefined();
    expect(pulpit!.getAttribute('aria-current')).toBe('page');

    const stanSystemu = buttons.find((b) => b.getAttribute('aria-label') === 'Stan systemu');
    expect(stanSystemu).toBeDefined();
    expect(stanSystemu!.getAttribute('aria-current')).toBeNull();
  });

  it('calls onNavigate with correct AppView when clicking a nav item', () => {
    const { onNavigate } = renderNav('system-status');
    const pulpitButton = screen.getByLabelText('Pulpit');
    fireEvent.click(pulpitButton);
    expect(onNavigate).toHaveBeenCalledWith('dashboard');

    const stanButton = screen.getByLabelText('Stan systemu');
    fireEvent.click(stanButton);
    expect(onNavigate).toHaveBeenCalledWith('system-status');
  });

  it('has semantic nav role', () => {
    const { container } = renderNav();
    expect(container.querySelector('nav')).toHaveAttribute('aria-label', 'Główna nawigacja');
  });
});