/**
 * Session types and an in-memory session store.
 */

import type { Principal } from '../principal';

export interface AuthSession {
  principal: Principal;
  /** ISO-8601 expiry timestamp. */
  expiresAt: string;
  idleExpiresAt?: string;
}

export interface AuthProvider {
  /** Resolve a bearer token to a session, or `null` when invalid. */
  authenticate(token: string): Promise<AuthSession | null>;
}

export class InMemorySessionStore {
  readonly #sessions = new Map<string, AuthSession>();

  set(token: string, session: AuthSession): void {
    this.#sessions.set(token, session);
  }

  get(token: string): AuthSession | undefined {
    const session = this.#sessions.get(token);
    if (!session) return undefined;
    if (new Date(session.expiresAt).getTime() <= Date.now()) {
      this.#sessions.delete(token);
      return undefined;
    }
    return session;
  }

  revoke(token: string): boolean {
    return this.#sessions.delete(token);
  }

  clearExpired(): number {
    let removed = 0;
    for (const [token, session] of this.#sessions) {
      if (new Date(session.expiresAt).getTime() <= Date.now()) {
        this.#sessions.delete(token);
        removed += 1;
      }
    }
    return removed;
  }
}
