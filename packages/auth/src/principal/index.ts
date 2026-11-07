/**
 * Principal identity types and helpers.
 */

export type PrincipalType = 'user' | 'agent' | 'service';

export type Role = 'admin' | 'governance' | 'manager' | 'employee' | 'service';

export interface Principal {
  id: string;
  type: PrincipalType;
  displayName: string;
  roles: readonly Role[];
}

export function hasRole(principal: Principal, role: Role): boolean {
  return principal.roles.includes(role);
}

export function hasAnyRole(principal: Principal, roles: readonly Role[]): boolean {
  return roles.some((role) => principal.roles.includes(role));
}
