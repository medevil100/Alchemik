import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * KROK 8.4B — same-origin proxy.
 *
 * Kontrakt (korekta właściciela 8.4B):
 * - klient wysyła pełne względne ścieżki /api/v1/... (trasy backendu);
 * - Vite server.proxy i preview.proxy przekazują /api do FastAPI BEZ rewrite;
 * - /health jest przekazywane osobno i bez rewrite;
 * - target proxy z ALCHEMIK_API_PROXY_TARGET (zmienna Node/Vite, nie VITE_*);
 * - bez zmiennej używany jest lokalny default 127.0.0.1:8000 (FastAPI port 8000);
 * - brak CORS (same-origin w przeglądarce);
 * - target nie trafia do produkcyjnego bundle (brak VITE_*).
 */

export const API_PROXY_DEFAULT_TARGET = 'http://127.0.0.1:8000';

export function getApiProxyTarget(): string {
  // process istnieje w Node (runtime Vite), ale bez @types/node używamy globalThis.
  const processLike = (globalThis as unknown as {
    process?: { env?: Record<string, string | undefined> };
  }).process;
  const envTarget = processLike?.env?.ALCHEMIK_API_PROXY_TARGET;
  return envTarget && envTarget.trim().length > 0
    ? envTarget.trim()
    : API_PROXY_DEFAULT_TARGET;
}

function apiProxy(): Record<string, { target: string; changeOrigin: boolean }> {
  const target = getApiProxyTarget();
  return {
    '/api': {
      target,
      changeOrigin: true,
    },
    '/health': {
      target,
      changeOrigin: true,
    },
  };
}

export function getApiProxyConfig(): ReturnType<typeof apiProxy> {
  return apiProxy();
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: apiProxy(),
  },
  preview: {
    port: 4173,
    proxy: apiProxy(),
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/tests/setup.ts',
    css: {
      modules: {
        classNameStrategy: 'non-scoped',
      },
    },
  },
});