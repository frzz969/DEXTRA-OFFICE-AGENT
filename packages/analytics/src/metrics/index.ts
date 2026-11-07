/**
 * Metric registry and aggregation helpers.
 */

export interface MetricPoint {
  name: string;
  value: number;
  /** ISO-8601 timestamp. */
  timestamp: string;
  labels?: Record<string, string>;
}

export interface MetricQuery {
  name: string;
  from: string;
  to: string;
  labels?: Record<string, string>;
}

export class MetricRegistry {
  readonly #points: MetricPoint[] = [];

  record(point: MetricPoint): void {
    this.#points.push(point);
  }

  query(query: MetricQuery): readonly MetricPoint[] {
    const from = new Date(query.from).getTime();
    const to = new Date(query.to).getTime();
    return this.#points.filter((point) => {
      if (point.name !== query.name) return false;
      const time = new Date(point.timestamp).getTime();
      if (time < from || time > to) return false;
      if (query.labels) {
        for (const [key, value] of Object.entries(query.labels)) {
          if (point.labels?.[key] !== value) return false;
        }
      }
      return true;
    });
  }

  aggregate(name: string, query?: Omit<MetricQuery, 'name'>): number {
    const points = query ? this.query({ name, ...query }) : this.#points.filter((p) => p.name === name);
    return points.reduce((total, point) => total + point.value, 0);
  }

  clear(): void {
    this.#points.length = 0;
  }
}

export function average(points: readonly MetricPoint[]): number {
  if (points.length === 0) return 0;
  return points.reduce((total, point) => total + point.value, 0) / points.length;
}
