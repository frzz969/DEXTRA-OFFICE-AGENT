/**
 * Interval-based scheduler with no external dependencies.
 */

export interface ScheduledJob {
  id: string;
  intervalMs: number;
  running: boolean;
}

export class IntervalScheduler {
  readonly #jobs = new Map<string, { timer: ReturnType<typeof setInterval>; handler: () => void | Promise<void> }>();

  schedule(id: string, handler: () => void | Promise<void>, intervalMs: number): ScheduledJob {
    this.cancel(id);
    const timer = setInterval(() => {
      void handler();
    }, intervalMs);
    this.#jobs.set(id, { timer, handler });
    return { id, intervalMs, running: true };
  }

  cancel(id: string): boolean {
    const job = this.#jobs.get(id);
    if (!job) return false;
    clearInterval(job.timer);
    this.#jobs.delete(id);
    return true;
  }

  cancelAll(): void {
    for (const id of [...this.#jobs.keys()]) this.cancel(id);
  }

  has(id: string): boolean {
    return this.#jobs.has(id);
  }
}
