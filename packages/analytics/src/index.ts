/**
 * `@dextra/analytics` — metrics ingestion and query contracts.
 */

export * from './metrics';
export * from './reports';

export interface AnalyticsSink {
  record(point: MetricPoint): void;
  query(query: MetricQuery): Promise<readonly MetricPoint[]>;
}

import type { MetricPoint, MetricQuery } from './metrics';
