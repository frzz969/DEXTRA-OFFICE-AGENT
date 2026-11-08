/**
 * Authorization contract — the single source of truth shared by the MCP server
 * and anything that needs to describe what a caller may do.
 *
 * There are three distinct ideas here and they must not be conflated:
 *
 *   Scope       what a token is: `agent` (read + plan) or `ops` (write/execute).
 *   Capability  a named permission the UI and the server both reason about.
 *   Tool        a concrete MCP operation; each tool requires exactly one capability.
 *
 * The tool allowlist is DERIVED from (scope -> capabilities -> tools) rather
 * than maintained as a second hand-written list. That is deliberate: a
 * hand-written allowlist can drift from the capability story, and drift in an
 * authorization table is a security defect, not a typo.
 *
 * A capability that no scope grants is not a bug in this file — it is a
 * statement that the server does not implement that authorization yet. The
 * dashboard renders those as "not available", never as "denied", because no
 * decision was ever made.
 *
 * This file is intentionally dependency-free TypeScript so it can be consumed
 * by the web app, the MCP server tooling, and the Python parity test alike.
 */

export const SCOPES = ['agent', 'ops'] as const;
export type Scope = (typeof SCOPES)[number];

/**
 * Capability vocabulary. Keys match the dashboard's existing permission matrix
 * so there is one vocabulary on both sides, not a translation layer that can
 * disagree with itself.
 */
export const CAPABILITIES = [
  'view_own',
  'view_all',
  'create_request',
  'approve',
  'issue_mandate',
  'revoke_mandate',
  'execute',
  'view_audit',
  'edit_policy',
  'manage_users',
  'manage_integrations',
] as const;
export type Capability = (typeof CAPABILITIES)[number];

/** Every tool the server exposes, with the capability it requires. */
export const TOOL_CAPABILITY = {
  get_org_rules: 'view_all',
  find_precedent: 'view_all',
  create_plan: 'create_request',
  /*
   * Intake lengkap Office Agent: normalisasi, dekomposisi, klarifikasi, dan
   * plan. Ia membuat permintaan/plan, jadi kewenangannya sama dengan
   * create_plan; tidak ada model otorisasi baru.
   */
  office_agent_run: 'create_request',
  validate_plan: 'create_request',
  get_plan: 'view_all',
  list_plans: 'view_all',
  request_approval_challenge: 'approve',
  submit_approval: 'approve',
  get_mandate: 'view_all',
  list_mandates: 'view_all',
  issue_mandate: 'issue_mandate',
  execute_action: 'execute',
  revoke_mandate: 'revoke_mandate',
  list_executions: 'view_all',
  get_status: 'view_all',
  get_audit_log: 'view_audit',
  /*
   * Export writes a file, but it reads the audit log — and the audit log is
   * exactly what that authority governs. A separate capability would be a new
   * authorization concept for the same authority.
   */
  export_audit: 'view_audit',
  list_alerts: 'view_audit',
  get_caller_context: 'view_own',
  list_specialists: 'view_all',
} as const satisfies Record<string, Capability>;

export type ToolName = keyof typeof TOOL_CAPABILITY;
export const TOOL_NAMES = Object.keys(TOOL_CAPABILITY) as ToolName[];

/**
 * What each scope grants. Nothing here is inherited implicitly: a scope gets
 * exactly the capabilities listed, and a capability missing from both scopes is
 * unimplemented server-side.
 *
 * `view_own` is granted, but note its limitation: the server records no owner
 * on a plan, so "own" cannot be filtered. See IDENTITY_AUTHORIZATION_MODEL.md.
 */
export const SCOPE_CAPABILITIES: Record<Scope, readonly Capability[]> = {
  agent: ['view_own', 'view_all', 'create_request'],
  ops: [
    'view_own',
    'view_all',
    'create_request',
    'approve',
    'issue_mandate',
    'revoke_mandate',
    'execute',
    'view_audit',
  ],
};

/**
 * Capabilities present in the vocabulary that no scope grants. These are the
 * honest "not implemented" list: admin functions and policy editing have no
 * server-side authorization and no backing tool.
 */
export const UNBACKED_CAPABILITIES: readonly Capability[] = CAPABILITIES.filter(
  (cap) => !SCOPES.some((scope) => SCOPE_CAPABILITIES[scope].includes(cap)),
);

export function capabilitiesForScope(scope: Scope): Capability[] {
  return [...SCOPE_CAPABILITIES[scope]];
}

/** Tools a scope may call, derived from capabilities. Never hand-maintained. */
export function toolsForScope(scope: Scope): ToolName[] {
  const caps = SCOPE_CAPABILITIES[scope];
  return TOOL_NAMES.filter((tool) => caps.includes(TOOL_CAPABILITY[tool]));
}

/** True when the scope holds the capability the tool requires. */
export function scopeAllowsTool(scope: Scope, tool: string): boolean {
  if (!Object.hasOwn(TOOL_CAPABILITY, tool)) return false;
  const required = TOOL_CAPABILITY[tool as ToolName];
  return SCOPE_CAPABILITIES[scope].includes(required);
}

/** True when some scope could ever hold this capability. Unknown caps are false. */
export function isKnownCapability(cap: string): cap is Capability {
  return (CAPABILITIES as readonly string[]).includes(cap);
}
