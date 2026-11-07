/**
 * Governance contracts.
 */

import type { RiskLevel } from '../domain';

export interface GovernancePolicy {
  id: string;
  name: string;
  scope: string;
  boundaryType: 'read' | 'analyze' | 'recommend' | 'prepare' | 'execute';
  humanApprovalThreshold: string;
  isEnforced: boolean;
  lastUpdated: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  actorType: 'user' | 'agent' | 'system';
  actorId: string;
  actorName: string;
  action: string;
  targetResource: string;
  riskLevel: RiskLevel;
  result: 'success' | 'blocked' | 'requires_approval' | 'failed';
  approvalId?: string;
  hash: string;
  details: string;
}
