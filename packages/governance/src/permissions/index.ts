/**
 * Permission tiers, role capability tables and governance decisions.
 */

export type PermissionTier = 'read' | 'analyze' | 'recommend' | 'prepare' | 'execute';

export const PERMISSION_TIERS: readonly PermissionTier[] = [
  'read',
  'analyze',
  'recommend',
  'prepare',
  'execute',
];

export type GovernanceRole = 'admin' | 'governance' | 'manager' | 'employee' | 'service';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface PermissionGrant {
  tier: PermissionTier;
  /** Resource selector, e.g. `hr.employees`, `finance.payroll`. */
  resource: string;
}

export interface GovernanceDecision {
  allowed: boolean;
  requiresApproval: boolean;
  tier: PermissionTier;
  riskLevel: RiskLevel;
  reason: string;
}

/** Ordered capability table. Higher tiers subsume lower tiers. */
export const ROLE_CAPABILITIES: Readonly<Record<GovernanceRole, readonly PermissionTier[]>> = {
  admin: PERMISSION_TIERS,
  governance: ['read', 'analyze', 'recommend', 'prepare', 'execute'],
  manager: ['read', 'analyze', 'recommend', 'prepare'],
  employee: ['read', 'analyze'],
  service: ['read', 'analyze', 'recommend', 'prepare', 'execute'],
};

export function tierRank(tier: PermissionTier): number {
  return PERMISSION_TIERS.indexOf(tier);
}

export function tierRequiresApproval(tier: PermissionTier): boolean {
  return tier === 'prepare' || tier === 'execute';
}

export function roleHasTier(role: GovernanceRole, tier: PermissionTier): boolean {
  return (ROLE_CAPABILITIES[role] ?? []).includes(tier);
}
