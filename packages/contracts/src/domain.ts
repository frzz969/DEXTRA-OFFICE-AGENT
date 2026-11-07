/**
 * DEXTRA cross-cutting domain primitives.
 *
 * Shared between the application layer, the API and the intelligence/governance
 * packages. Domain-specific types live in their own modules under `src/`.
 */

/** Route-level view identifiers. Each maps 1:1 to a dashboard route. */
export type ViewMode =
  | 'overview'
  | 'ai-workspace'
  | 'tasks'
  | 'agents'
  | 'hr'
  | 'finance'
  | 'inventory'
  | 'operations'
  | 'analytics'
  | 'reports'
  | 'approvals'
  | 'governance'
  | 'audit-logs'
  | 'integrations'
  | 'settings';

export const VIEW_PATHS: Record<ViewMode, string> = {
  overview: '/overview',
  'ai-workspace': '/ai-workspace',
  tasks: '/tasks',
  agents: '/agents',
  hr: '/hr',
  finance: '/finance',
  inventory: '/inventory',
  operations: '/operations',
  analytics: '/analytics',
  reports: '/reports',
  approvals: '/approvals',
  governance: '/governance',
  'audit-logs': '/audit-logs',
  integrations: '/integrations',
  settings: '/settings',
};

export function viewPath(view: ViewMode): string {
  return VIEW_PATHS[view];
}

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

/** Integration service descriptor used by the integrations view. */
export interface IntegrationService {
  id: string;
  name: string;
  category: string;
  description: string;
  status: 'connected' | 'syncing' | 'disconnected' | 'error';
  lastSync: string;
  recordsSynced: number;
  healthPercent: number;
  icon: string;
}

/** In-app notification item. */
export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  type: 'approval' | 'system' | 'agent' | 'alert';
  isRead: boolean;
  linkView?: ViewMode;
}
