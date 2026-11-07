/**
 * Integration adapter contracts, including an ERP-style adapter.
 */

export type IntegrationStatus = 'connected' | 'syncing' | 'disconnected' | 'error';

export interface IntegrationDescriptor {
  id: string;
  name: string;
  category: string;
  status: IntegrationStatus;
  /** ISO-8601 timestamp of last successful sync, if any. */
  lastSync?: string;
}

export interface IntegrationAdapter {
  readonly id: string;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  healthCheck(): Promise<IntegrationStatus>;
}

export interface ErpAdapter extends IntegrationAdapter {
  pullRecords(entity: string, since?: string): Promise<readonly Record<string, unknown>[]>;
  pushRecord(entity: string, record: Record<string, unknown>): Promise<{ id: string }>;
}
