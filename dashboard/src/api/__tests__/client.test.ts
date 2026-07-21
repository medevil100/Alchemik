/**
 * Testy klienta HTTP — symulacja fetch przez vi.fn().
 * Obejmują: sukces, błąd HTTP, błąd sieciowy, timeout, niepoprawny JSON, walidację.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get, ApiHttpError, ApiNetworkError, ApiTimeoutError, ApiValidationError } from '../client';


const mockFetch = vi.fn();

beforeEach(() => {
  vi.restoreAllMocks();
  globalThis.fetch = mockFetch;
});

// ---------------------------------------------------------------------------
// Pomocnicze
// ---------------------------------------------------------------------------

function mockJsonResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: (name: string) => name === 'content-type' ? 'application/json' : null,
    },
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  };
}

function mockEmptyJsonResponse() {
  return {
    ok: true,
    status: 200,
    headers: {
      get: () => 'application/json',
    },
    json: () => Promise.reject(new SyntaxError('Unexpected end of JSON input')),
    text: () => Promise.resolve(''),
  };
}

// ---------------------------------------------------------------------------
// Testy
// ---------------------------------------------------------------------------

describe('client.get()', () => {
  it('zwraca dane dla poprawnej odpowiedzi JSON', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({ status: 'ok', api: 'running', database: 'available', journal_mode: 'wal', schema_version: 1, cycle_count: 0, event_count: 0 }));
    const result = await get<Record<string, unknown>>('/health');
    expect(result).toBeDefined();
    expect(result.status).toBe('ok');
  });

  it('rzuca ApiHttpError dla statusu 404', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({ detail: 'Not found' }, 404));
    await expect(get('/api/v1/cycles/nonexistent')).rejects.toThrow(ApiHttpError);
    await expect(get('/api/v1/cycles/nonexistent')).rejects.toThrow('Not found');
  });

  it('rzuca ApiHttpError z kodem statusu', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({ detail: 'Server error' }, 500));
    try {
      await get('/api/v1/dashboard');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiHttpError);
      expect((e as ApiHttpError).statusCode).toBe(500);
    }
  });

  it('rzuca ApiNetworkError przy TypeError (fetch nieosiągalny)', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(get('/health')).rejects.toThrow(ApiNetworkError);
  });

  it('rzuca ApiTimeoutError po przekroczeniu czasu', async () => {
    // Symulacja AbortController rejection
    const abortError = new DOMException('The operation was aborted', 'AbortError');
    mockFetch.mockRejectedValue(abortError);
    await expect(get('/health')).rejects.toThrow(ApiTimeoutError);
  });

  it('rzuca ApiValidationError przy niepoprawnym JSON', async () => {
    mockFetch.mockResolvedValue(mockEmptyJsonResponse());
    await expect(get('/health')).rejects.toThrow(ApiValidationError);
  });

  it('rzuca ApiValidationError przy braku wymaganych pól w health', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({ status: 'ok' })); // brak api, database, etc.
    await expect(get('/health')).rejects.toThrow(ApiValidationError);
  });

  it('akceptuje poprawną odpowiedź health z walidacją', async () => {
    const validHealth = {
      status: 'ok',
      api: 'running',
      database: 'available',
      journal_mode: 'wal',
      schema_version: 1,
      cycle_count: 5,
      event_count: 10,
    };
    mockFetch.mockResolvedValue(mockJsonResponse(validHealth));
    const result = await get('/health');
    expect(result).toEqual(validHealth);
  });

  it('buduje URL z parametrami query', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({ items: [], limit: 10, offset: 0, returned: 0 }));
    await get('/api/v1/market-events', { limit: 10, ticker: 'TST' });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('limit=10'),
      expect.anything(),
    );
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('ticker=TST'),
      expect.anything(),
    );
  });

  it('używa AbortController (sprawdza signal)', async () => {
    const validData = { status: 'ok', api: 'running', database: 'available', journal_mode: 'wal', schema_version: 1, cycle_count: 0, event_count: 0 };
    mockFetch.mockResolvedValue(mockJsonResponse(validData));
    await get('/health');
    const callArgs = mockFetch.mock.calls[0][1];
    expect(callArgs).toHaveProperty('signal');
    expect(callArgs.signal).toBeInstanceOf(AbortSignal);
  });

  it('ustawia Accept header', async () => {
    const validData = { status: 'ok', api: 'running', database: 'available', journal_mode: 'wal', schema_version: 1, cycle_count: 0, event_count: 0 };
    mockFetch.mockResolvedValue(mockJsonResponse(validData));
    await get('/health');
    const headers = mockFetch.mock.calls[0][1].headers;
    expect(headers['Accept']).toBe('application/json');
  });
});

describe('client.buildUrl (przez get)', () => {
  it('koduje parametry ścieżki', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({}));
    await get('/api/v1/tickers/ABC.WA/market-events');
    const url = mockFetch.mock.calls[0][0];
    expect(url).toContain('ABC.WA');
  });
});