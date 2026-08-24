// @vitest-environment node
/**
 * KROK 8.4B — test konfiguracji same-origin proxy w vite.config.ts.
 * Uruchamiany przez Vitest (pliki *.test.ts w src/tests są wykrywane
 * przez domyślny include, w przeciwieństwie do vite.config.*).
 */
import { describe, it, expect, afterEach, vi } from 'vitest';
import {
  getApiProxyConfig,
  getApiProxyTarget,
  API_PROXY_DEFAULT_TARGET,
  default as viteConfig,
} from '../../vite.config';

describe('KROK 8.4B — Vite dev/preview same-origin proxy', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('server.proxy zawiera klucz "/api"', () => {
    expect(viteConfig.server).toBeDefined();
    expect(viteConfig.server!.proxy).toBeDefined();
    expect(Object.keys(viteConfig.server!.proxy!)).toContain('/api');
  });

  it('preview.proxy zawiera klucz "/api" (identyczny kontrakt jak dev)', () => {
    expect(viteConfig.preview).toBeDefined();
    expect(viteConfig.preview!.proxy).toBeDefined();
    expect(Object.keys(viteConfig.preview!.proxy!)).toContain('/api');
  });

  it('dev i preview mają zgodny target dla /api', () => {
    const dev = viteConfig.server!.proxy!['/api'] as { target?: string };
    const preview = viteConfig.preview!.proxy!['/api'] as { target?: string };
    expect(dev.target).toBeDefined();
    expect(preview.target).toBeDefined();
    expect(preview.target).toBe(dev.target);
  });

  it('proxy /api NIE usuwa prefiksu (brak rewrite) — backend otrzymuje pełne /api/v1/...', () => {
    const dev = viteConfig.server!.proxy!['/api'] as { rewrite?: unknown };
    const preview = viteConfig.preview!.proxy!['/api'] as { rewrite?: unknown };
    expect(dev.rewrite).toBeUndefined();
    expect(preview.rewrite).toBeUndefined();
  });

  it('proxy /health jest przekazywane osobno i bez rewrite', () => {
    const serverKeys = Object.keys(viteConfig.server!.proxy!);
    const previewKeys = Object.keys(viteConfig.preview!.proxy!);
    expect(serverKeys).toContain('/health');
    expect(previewKeys).toContain('/health');
    const dev = viteConfig.server!.proxy!['/health'] as { rewrite?: unknown };
    expect(dev.rewrite).toBeUndefined();
  });

  it('target pochodzi z ALCHEMIK_API_PROXY_TARGET (zmienna Node/Vite, nie VITE_*)', () => {
    vi.stubEnv('ALCHEMIK_API_PROXY_TARGET', 'http://127.0.0.1:9999');
    vi.stubEnv('VITE_API_URL', '');
    expect(getApiProxyTarget()).toBe('http://127.0.0.1:9999');
  });

  it('domyślny target to lokalny default FastAPI 127.0.0.1:8000', () => {
    vi.stubEnv('ALCHEMIK_API_PROXY_TARGET', '');
    expect(getApiProxyTarget()).toBe(API_PROXY_DEFAULT_TARGET);
    expect(API_PROXY_DEFAULT_TARGET).toBe('http://127.0.0.1:8000');
    const map = getApiProxyConfig();
    expect((map['/api'] as { target?: string }).target).toBe('http://127.0.0.1:8000');
  });

  it('konfiguracja proxy nie zawiera CORS', () => {
    const map = getApiProxyConfig();
    const dev = map['/api'] as Record<string, unknown>;
    expect(Object.keys(dev)).not.toContain('cors');
  });
});