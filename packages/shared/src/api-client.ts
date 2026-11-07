/**
 * Typed client for the DEXTRA API endpoints.
 */

import { fetchJson } from './http';

export interface DextraApiClientOptions {
  baseUrl?: string;
  csrfToken?: string;
  credentials?: RequestCredentials;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface LoginResponse {
  authenticated: boolean;
  csrf_token?: string;
  principal?: Record<string, unknown>;
}

export interface OverviewResponse {
  generated_at: string;
  kpi: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ApprovalItem {
  id: string;
  decision: string;
  [key: string]: unknown;
}

export interface AgentItem {
  id?: string;
  slug?: string;
  [key: string]: unknown;
}

export interface PolicyItem {
  id?: string;
  slug?: string;
  [key: string]: unknown;
}

export interface AuditEventItem {
  id: string;
  [key: string]: unknown;
}

export class DextraApiClient {
  readonly baseUrl: string;
  csrfToken?: string;
  readonly credentials: RequestCredentials;

  constructor(options: DextraApiClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? '').replace(/\/$/, '');
    this.csrfToken = options.csrfToken;
    this.credentials = options.credentials ?? 'include';
  }

  setCsrfToken(token: string): void {
    this.csrfToken = token;
  }

  async login(payload: LoginPayload): Promise<LoginResponse> {
    const result = await fetchJson<LoginResponse>(`${this.baseUrl}/api/v1/auth/login`, {
      method: 'POST',
      credentials: this.credentials,
      body: payload,
    });
    if (result.csrf_token) this.csrfToken = result.csrf_token;
    return result;
  }

  async overview(): Promise<OverviewResponse> {
    return fetchJson<OverviewResponse>(`${this.baseUrl}/api/v1/overview`, {
      credentials: this.credentials,
      csrfToken: this.csrfToken,
    });
  }

  async listApprovals(): Promise<{ items: ApprovalItem[] }> {
    return fetchJson<{ items: ApprovalItem[] }>(`${this.baseUrl}/api/v1/approvals`, {
      credentials: this.credentials,
      csrfToken: this.csrfToken,
    });
  }

  async listAgents(): Promise<{ items: AgentItem[] }> {
    return fetchJson<{ items: AgentItem[] }>(`${this.baseUrl}/api/v1/agents`, {
      credentials: this.credentials,
      csrfToken: this.csrfToken,
    });
  }

  async listPolicies(): Promise<{ items: PolicyItem[] }> {
    return fetchJson<{ items: PolicyItem[] }>(`${this.baseUrl}/api/v1/policies`, {
      credentials: this.credentials,
      csrfToken: this.csrfToken,
    });
  }

  async listAuditEvents(limit = 100): Promise<{ items: AuditEventItem[] }> {
    return fetchJson<{ items: AuditEventItem[] }>(
      `${this.baseUrl}/api/v1/audit-events?limit=${encodeURIComponent(String(limit))}`,
      {
        credentials: this.credentials,
        csrfToken: this.csrfToken,
      },
    );
  }
}
