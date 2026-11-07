/**
 * Typed fetch-based JSON client.
 */

export class HttpError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = 'HttpError';
  }
}

export interface HttpRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  body?: unknown;
  credentials?: RequestCredentials;
  csrfToken?: string;
  signal?: AbortSignal;
}

export async function fetchJson<T>(url: string, options: HttpRequestOptions = {}): Promise<T> {
  const response = await fetch(url, {
    method: options.method ?? 'GET',
    credentials: options.credentials ?? 'same-origin',
    headers: {
      Accept: 'application/json',
      ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(options.csrfToken ? { 'X-CSRF-Token': options.csrfToken } : {}),
      ...(options.headers ?? {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  const text = await response.text();
  let parsed: unknown;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!response.ok) {
    throw new HttpError(response.status, `Request failed with status ${response.status}`, parsed);
  }

  return parsed as T;
}

export async function safeFetchJson<T>(
  url: string,
  options?: HttpRequestOptions,
): Promise<Result<T, HttpError>> {
  try {
    return ok(await fetchJson<T>(url, options));
  } catch (error) {
    return err(error instanceof HttpError ? error : new HttpError(0, String(error)));
  }
}

import type { Result } from '../result';
import { ok, err } from '../result';
