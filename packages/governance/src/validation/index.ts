/**
 * Validation helpers for governed action payloads.
 */

export interface ValidationIssue {
  field: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
}

export function validateAction(input: {
  actorId?: string;
  tier?: string;
  resource?: string;
}): ValidationResult {
  const issues: ValidationIssue[] = [];
  if (!input.actorId) issues.push({ field: 'actorId', message: 'actorId is required' });
  if (!input.tier) issues.push({ field: 'tier', message: 'tier is required' });
  if (!input.resource) issues.push({ field: 'resource', message: 'resource is required' });
  return { valid: issues.length === 0, issues };
}
