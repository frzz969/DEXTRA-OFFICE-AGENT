/**
 * Rules that determine whether an action needs human approval.
 */

import type { PermissionTier, RiskLevel } from '../permissions';
import { tierRequiresApproval } from '../permissions';

export interface ApprovalRuleInput {
  tier: PermissionTier;
  riskLevel: RiskLevel;
  amount?: number;
}

export function requiresApproval(input: ApprovalRuleInput): boolean {
  if (tierRequiresApproval(input.tier)) return true;
  if (input.riskLevel === 'high' || input.riskLevel === 'critical') return true;
  if ((input.amount ?? 0) >= 10000) return true;
  return false;
}
