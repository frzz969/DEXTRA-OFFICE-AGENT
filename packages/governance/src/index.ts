/**
 * `@dextra/governance` — permission tiers and enforcement primitives.
 */

import type { GovernanceDecision, PermissionTier, RiskLevel } from './permissions';

export * from './permissions';
export * from './policies';
export * from './risk-classification';
export * from './approval-rules';
export * from './human-oversight';
export * from './authorization';
export * from './validation';
export * from './audit';

/** Backwards-compatible evaluator interface. */
export interface PolicyEvaluator {
  evaluate(input: {
    actorId: string;
    tier: PermissionTier;
    resource: string;
    riskLevel: RiskLevel;
  }): Promise<GovernanceDecision>;
}
