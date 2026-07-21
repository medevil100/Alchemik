/**
 * Centralny klient HTTP — abstrakcja nad natywnym fetch.
 * - Timeout przez AbortController
 * - Obsługa błędów sieciowych i HTTP
 * - Walidacja odpowiedzi (podstawowa kontrola typu runtime)
 */

import { API_CONFIG } from './config';
import type { HealthResponse } from './types';

// ---------------------------------------------------------------------------
// Typy błędów
// ---------------------------------------------------------------------------

export class ApiNetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiNetworkError';
  }
}

export class ApiTimeoutError extends Error {
  constructor() {
    super('Przekroczono czas oczekiwania na odpowiedź serwera.');
    this.name = 'ApiTimeoutError';
  }
}

export class ApiHttpError extends Error {
  public readonly statusCode: number;

  constructor(statusCode: number, message: string) {
    super(message);
    this.name = 'ApiHttpError';
    this.statusCode = statusCode;
  }
}

export class ApiValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiValidationError';
  }
}

export type ApiError = ApiNetworkError | ApiTimeoutError | ApiHttpError | ApiValidationError;

// ---------------------------------------------------------------------------
// Response helpers
// ---------------------------------------------------------------------------

function buildUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const base = API_CONFIG.BASE_URL;
  let url = base ? `${base}${path}` : path;

  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value));
      }
    }
    const qs = searchParams.toString();
    if (qs) {
      url += `?${qs}`;
    }
  }

  return url;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      // Await required here to catch JSON parse errors (e.g. SyntaxError)
      return await response.json();
    } catch {
      throw new ApiValidationError('Odpowiedź serwera nie jest poprawnym JSON.');
    }
  }
  const text = await response.text();
  if (text.length === 0) {
    throw new ApiValidationError('Serwer zwrócił pustą odpowiedź.');
  }
  return text;
}

// ---------------------------------------------------------------------------
// Runtime validation: sprawdza, czy wartość jest obiektem (nie null, nie array)
// ---------------------------------------------------------------------------

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// ---------------------------------------------------------------------------
// Minimalna walidacja HealthResponse dla ekranu technicznego
// ---------------------------------------------------------------------------

function validateHealthResponse(data: unknown): HealthResponse {
  if (!isRecord(data)) {
    throw new ApiValidationError('Health: oczekiwano obiektu.');
  }
  const requiredFields: (keyof HealthResponse)[] = ['status', 'api', 'database', 'journal_mode', 'schema_version', 'cycle_count', 'event_count'];
  for (const field of requiredFields) {
    if (!(field in data)) {
      throw new ApiValidationError(`Health: brak wymaganego pola "${field}".`);
    }
  }
  if (typeof data.schema_version !== 'number') {
    throw new ApiValidationError('Health: "schema_version" musi być liczbą.');
  }
  if (typeof data.cycle_count !== 'number') {
    throw new ApiValidationError('Health: "cycle_count" musi być liczbą.');
  }
  if (typeof data.event_count !== 'number') {
    throw new ApiValidationError('Health: "event_count" musi być liczbą.');
  }
  return data as unknown as HealthResponse;
}

// ---------------------------------------------------------------------------
// Publiczna mapa walidatorów (na przyszłość)
// ---------------------------------------------------------------------------

const validators: Record<string, (data: unknown) => unknown> = {
  '/health': validateHealthResponse,
};

// ---------------------------------------------------------------------------
// Core request
// ---------------------------------------------------------------------------

async function request<T>(
  method: string,
  path: string,
  params?: Record<string, string | number | undefined>,
  body?: unknown,
): Promise<T> {
  const url = buildUrl(path, params);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT_MS);

  try {
    const options: RequestInit = {
      method,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
      },
    };

    if (body !== undefined) {
      options.headers = {
        ...options.headers,
        'Content-Type': 'application/json',
      };
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    clearTimeout(timeoutId);

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const errorBody = await parseResponseBody(response);
        if (isRecord(errorBody) && typeof errorBody.detail === 'string') {
          detail = errorBody.detail;
        }
      } catch {
        // ignore parse errors in error response
      }
      throw new ApiHttpError(response.status, detail);
    }

    const data = await parseResponseBody(response);

    // Runtime validation: jeśli istnieje walidator dla tej ścieżki, wykonaj go
    if (validators[path]) {
      return validators[path](data) as T;
    }

    // Ogólna kontrola: odpowiedź musi być obiektem lub tablicą
    if (data === null || data === undefined) {
      throw new ApiValidationError('Serwer zwrócił pustą odpowiedź.');
    }

    return data as T;
  } catch (error: unknown) {
    clearTimeout(timeoutId);

    if (error instanceof ApiNetworkError || error instanceof ApiHttpError ||
        error instanceof ApiTimeoutError || error instanceof ApiValidationError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiTimeoutError();
    }

    if (error instanceof TypeError) {
      throw new ApiNetworkError(
        'Nie można połączyć się z serwerem. Sprawdź połączenie sieciowe.'
      );
    }

    throw error;
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function get<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  return request<T>('GET', path, params);
}

export async function getWithBody<T>(
  path: string,
  body: unknown,
): Promise<T> {
  return request<T>('GET', path, undefined, body);
}