/** Bentuk respons FastAPI yang dikonsumsi dashboard. Tidak mengubah kontrak backend. */

export interface PrincipalDto {
  principal_id: string;
  display_name: string;
  email: string;
  tenant_id: string;
  tenant_slug: string | null;
  role: string;
  capabilities: string[];
  mfa_enabled: boolean;
  pending_mfa: boolean;
}

export interface AuthSessionDto {
  authenticated: boolean;
  auth_kind: string;
  pending_mfa: boolean;
  scope: string;
  capabilities: string[];
  principal: Record<string, unknown> | null;
  tenant?: { id: string; slug: string | null };
  role?: string;
  mfa_enabled?: boolean;
}

export interface LoginResponseDto {
  authenticated: boolean;
  mfa_required: boolean;
  principal: PrincipalDto;
  session: { id: string; expires_at: string; idle_expires_at: string };
  csrf_token?: string;
}

/** GET /api/v1/approvals — keputusan yang sudah tercatat. */
export interface ApprovalDecisionDto {
  id: string;
  plan_id: string;
  approver_id: string;
  decision: 'approved' | 'rejected' | 'revision' | 'pending' | string;
  reason: string;
  decided_at: string;
  mandate_id: string | null;
}

export interface ApprovalsListDto {
  items: ApprovalDecisionDto[];
  note?: string;
}

export interface OfficeActionDto {
  action_id: string;
  action_type: string;
  params?: Record<string, unknown>;
  source_ref?: Record<string, unknown>;
}

/** GET /api/v1/office-agent/plans — rencana yang menunggu keputusan manusia. */
export interface OfficePlanDto {
  id: string;
  request_id: string;
  plan_id: string;
  plan_hash: string;
  status: string;
  actions: OfficeActionDto[];
  findings?: unknown[];
  validation?: Record<string, unknown>;
  created_at: string;
}

export interface OfficePlansListDto {
  items: OfficePlanDto[];
}

export interface ApprovalDecisionResponseDto {
  approval_id: string;
  mandate_id: string | null;
  action_id: string;
  decision: string;
  next?: string;
}

/** GET /api/v1/audit-events */
export interface AuditEventDto {
  id: string;
  seq: number;
  at: string;
  event_type: string;
  actor: string;
  scope: string;
  action: string;
  resource: string;
  decision: string;
  plan_id: string;
  mandate_id: string;
  execution_id: string;
  correlation_id: string;
  detail: Record<string, unknown>;
  entry_hash: string;
}

export interface AuditEventsListDto {
  items: AuditEventDto[];
}

/** GET /api/v1/audit-events/verify */
export interface AuditVerifyDto {
  ok: boolean;
  checked: number;
  broken_at_seq?: number;
  chain_versions?: number[];
}

/** GET /api/v1/agents — DTO registry agen, bukan bentuk AIAgent mock. */
export interface AgentDto {
  id: string;
  slug: string;
  display_name: string;
  agent_type: string;
  description: string;
  model_provider: string;
  status: 'active' | 'idle' | 'busy' | 'disabled' | 'error' | string;
  is_enabled: boolean;
  capabilities: string[];
  versions: number;
}

export interface AgentsListDto {
  items: AgentDto[];
  expected_specialists: string[];
  unexpected: string[];
}
