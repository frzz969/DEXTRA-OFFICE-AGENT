/**
 * Result helpers and nominal typing utilities.
 */

export type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

export function ok<T>(value: T): Result<T, never> {
  return { ok: true, value };
}

export function err<E>(error: E): Result<never, E> {
  return { ok: false, error };
}

export function isOk<T, E>(result: Result<T, E>): result is { ok: true; value: T } {
  return result.ok;
}

export function isErr<T, E>(result: Result<T, E>): result is { ok: false; error: E } {
  return !result.ok;
}

/** Nominal typing helper, e.g. `Brand<string, 'UserId'>`. */
export type Brand<T, B extends string> = T & { readonly __brand: B };

export type Nullable<T> = T | null;

/** Narrow an array to its defined values. Useful with `noUncheckedIndexedAccess`. */
export function compact<T>(values: readonly (T | null | undefined)[]): T[] {
  return values.filter((value): value is T => value != null);
}
