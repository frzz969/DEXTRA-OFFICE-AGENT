/**
 * Klien HTTP tunggal untuk browser.
 *
 * Semua permintaan menuju same-origin proxy `/api/[...proxy]`, yang meneruskan
 * cookie sesi dan header CSRF ke FastAPI. Tidak ada fallback ke data mock dan
 * tidak ada kegagalan yang ditelan: setiap status non-2xx dilempar sebagai
 * `ApiError` bertipe.
 */

export interface ApiErrorBody {
  code?: string;
  message?: string;
  detail?: string | { code?: string; message?: string; [key: string]: unknown };
  [key: string]: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly details?: unknown;

  constructor(status: number, message: string, code?: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export type JsonBody = Record<string, unknown> | unknown[];

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  /** Akan di-JSON.stringify dan dikirim sebagai body. */
  body?: JsonBody;
}

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const prefix = `${name}=`;
  for (const part of document.cookie.split(';')) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

function parseJson(text: string): unknown {
  if (!text) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

function errorFromResponse(status: number, payload: unknown, statusText: string): ApiError {
  if (payload && typeof payload === 'object') {
    const body = payload as ApiErrorBody;
    const nested =
      body.detail && typeof body.detail === 'object' ? body.detail : undefined;

    const code = nested?.code ?? body.code;
    const message =
      nested?.message ??
      body.message ??
      (typeof body.detail === 'string' ? body.detail : undefined) ??
      statusText ??
      `Permintaan gagal (HTTP ${status}).`;

    return new ApiError(status, message, code, payload);
  }

  return new ApiError(
    status,
    typeof payload === 'string' && payload ? payload : statusText || `Permintaan gagal (HTTP ${status}).`,
    undefined,
    payload
  );
}

export async function apiFetch<T>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const { body, headers: extraHeaders, method: requestedMethod, ...rest } = options;
  const method = requestedMethod ?? (body === undefined ? 'GET' : 'POST');

  const headers = new Headers(extraHeaders);
  headers.set('Accept', 'application/json');

  if (body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }

  if (method !== 'GET' && method !== 'HEAD') {
    const csrf = readCookie('dextra_csrf');
    if (csrf) headers.set('X-CSRF-Token', csrf);
  }

  let response: Response;
  try {
    response = await fetch(path, {
      ...rest,
      method,
      headers,
      credentials: 'include',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    throw new ApiError(
      0,
      'Tidak dapat menghubungi server. Periksa koneksi lalu coba lagi.',
      'network_error',
      error
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const payload = parseJson(text);

  if (!response.ok) {
    throw errorFromResponse(response.status, payload ?? text, response.statusText);
  }

  return (payload ?? text) as T;
}

export const api = {
  get: <T>(path: string, options?: ApiRequestOptions) =>
    apiFetch<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: JsonBody, options?: ApiRequestOptions) =>
    apiFetch<T>(path, { ...options, method: 'POST', body }),
};
