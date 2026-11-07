/**
 * Approval contracts.
 */

import type { RiskLevel } from '../domain';

export type ActionType =
  | 'leave_approval'
  | 'payroll_disbursement'
  | 'procurement_po'
  | 'financial_transfer'
  | 'employee_record_update'
  | 'policy_override';

export interface ApprovalRequest {
  id: string;
  title: string;
  requestingAgentId: string;
  requestingAgentName: string;
  department: string;
  actionType: ActionType;
  businessJustification: string;
  riskLevel: RiskLevel;
  amount?: number;
  currency?: string;
  supportingData: Record<string, unknown>;
  status: 'pending' | 'approved' | 'rejected' | 'changes_requested';
  createdAt: string;
  reviewedBy?: string;
  reviewedAt?: string;
  notes?: string;
}
