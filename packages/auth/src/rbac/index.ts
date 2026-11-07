/**
 * Role-based access control helpers.
 */

import type { Role } from '../principal';

const ROLE_RANK: Readonly<Record<Role, number>> = {
  employee: 1,
  manager: 2,
  governance: 3,
  service: 3,
  admin: 4,
};

export function roleRank(role: Role): number {
  return ROLE_RANK[role];
}

export function hasMinimumRole(roles: readonly Role[], minimum: Role): boolean {
  return roles.some((role) => roleRank(role) >= roleRank(minimum));
}

export function isAdmin(roles: readonly Role[]): boolean {
  return roles.includes('admin');
}
