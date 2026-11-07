/**
 * Deterministic risk classifier.
 */

import type { RiskLevel } from '../permissions';

export interface RiskInput {
  actionType?: string;
  amount?: number;
  resource?: string;
  destructive?: boolean;
}

export function classifyRisk(input: RiskInput): RiskLevel {
  const action = (input.actionType ?? '').toLowerCase();
  const amount = input.amount ?? 0;

  if (action === 'policy_override' || input.destructive) return 'critical';
  if (action === 'financial_transfer' && amount >= 100000) return 'critical';
  if (action === 'payroll_disbursement') return amount >= 50000 ? 'high' : 'medium';
  if (action === 'procurement_po') return amount >= 25000 ? 'high' : 'medium';
  if (action === 'financial_transfer') return amount >= 10000 ? 'high' : 'medium';
  if (action === 'employee_record_update') return 'medium';
  if (action === 'leave_approval') return 'low';
  if (amount >= 100000) return 'critical';
  if (amount >= 10000) return 'high';
  if (amount >= 1000) return 'medium';
  return 'low';
}
