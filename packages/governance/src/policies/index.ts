/**
 * Pure policy evaluator. Deny overrides review overrides allow.
 */

import type { GovernanceDecision, PermissionTier, RiskLevel } from '../permissions';

export type PolicyEffect = 'allow' | 'review' | 'deny';

export interface PolicyRule {
  id: string;
  resource: string;
  tier: PermissionTier;
  effect: PolicyEffect;
  reason?: string;
}

export interface PolicyEvaluationInput {
  actorId: string;
  tier: PermissionTier;
  resource: string;
  riskLevel: RiskLevel;
  rules: readonly PolicyRule[];
}

export function evaluatePolicies(input: PolicyEvaluationInput): GovernanceDecision {
  const applicable = input.rules.filter(
    (rule) => rule.resource === input.resource || rule.resource === '*',
  );

  let decision: PolicyEffect = 'allow';
  let reason = 'No matching policy; default allow.';

  if (applicable.some((rule) => rule.effect === 'deny')) {
    decision = 'deny';
    reason = applicable.find((rule) => rule.effect === 'deny')?.reason ?? 'Denied by policy.';
  } else if (applicable.some((rule) => rule.effect === 'review')) {
    decision = 'review';
    reason = applicable.find((rule) => rule.effect === 'review')?.reason ?? 'Review required by policy.';
  } else if (applicable.some((rule) => rule.effect === 'allow')) {
    decision = 'allow';
    reason = applicable.find((rule) => rule.effect === 'allow')?.reason ?? 'Allowed by policy.';
  } else {
    decision = 'deny';
    reason = 'No allow rule matched.';
  }

  return {
    allowed: decision === 'allow',
    requiresApproval: decision === 'review',
    tier: input.tier,
    riskLevel: input.riskLevel,
    reason,
  };
}
