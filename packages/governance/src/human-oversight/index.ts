/**
 * Human oversight checkpoints for governed actions.
 */

import type { GovernanceDecision } from '../permissions';

export interface OversightCheckpoint {
  id: string;
  label: string;
  required: boolean;
}

export function buildOversightCheckpoints(decision: GovernanceDecision): OversightCheckpoint[] {
  const checkpoints: OversightCheckpoint[] = [
    { id: 'policy', label: 'Policy evaluation', required: true },
    { id: 'risk', label: `Risk level ${decision.riskLevel}`, required: true },
  ];
  if (decision.requiresApproval) {
    checkpoints.push({ id: 'approval', label: 'Human approval', required: true });
  }
  return checkpoints;
}

export function requiresHumanOversight(decision: GovernanceDecision): boolean {
  return decision.requiresApproval || decision.riskLevel === 'critical';
}
