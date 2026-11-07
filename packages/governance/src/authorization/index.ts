/**
 * Authorization helpers built on role capability tables.
 */

import type { GovernanceRole, PermissionTier } from '../permissions';
import { ROLE_CAPABILITIES, tierRank } from '../permissions';

export interface AuthorizationInput {
  roles: readonly GovernanceRole[];
  requiredTier: PermissionTier;
  resource?: string;
}

export function authorize(input: AuthorizationInput): boolean {
  return input.roles.some((role) => {
    const capabilities = ROLE_CAPABILITIES[role] ?? [];
    return capabilities.some((tier) => tierRank(tier) >= tierRank(input.requiredTier));
  });
}

export function hasCapability(roles: readonly GovernanceRole[], tier: PermissionTier): boolean {
  return authorize({ roles, requiredTier: tier });
}
