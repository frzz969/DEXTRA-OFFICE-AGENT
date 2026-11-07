/**
 * Workflow trigger contracts.
 */

export type WorkflowTriggerType = 'event' | 'schedule' | 'manual';

export interface WorkflowTrigger {
  type: WorkflowTriggerType;
  event?: string;
  cron?: string;
  description?: string;
}
