/**
 * Append-only audit log with a SHA-256 hash chain.
 */

import { createHash } from 'node:crypto';

export interface AuditEvent {
  id: string;
  timestamp: string;
  actorId: string;
  action: string;
  resource: string;
  riskLevel: string;
  result: string;
  hash: string;
  previousHash: string;
}

export class AuditChain {
  readonly #events: AuditEvent[] = [];

  append(input: Omit<AuditEvent, 'hash' | 'previousHash'>): AuditEvent {
    const previousHash = this.#events.at(-1)?.hash ?? '';
    const payload = JSON.stringify({ ...input, previousHash });
    const hash = createHash('sha256').update(payload).digest('hex');
    const event: AuditEvent = { ...input, previousHash, hash };
    this.#events.push(event);
    return event;
  }

  list(): readonly AuditEvent[] {
    return [...this.#events];
  }

  verify(): boolean {
    let previousHash = '';
    for (const event of this.#events) {
      if (event.previousHash !== previousHash) return false;
      const { hash, ...rest } = event;
      const recalculated = createHash('sha256')
        .update(JSON.stringify({ ...rest, previousHash: event.previousHash }))
        .digest('hex');
      if (recalculated !== hash) return false;
      previousHash = hash;
    }
    return true;
  }
}
