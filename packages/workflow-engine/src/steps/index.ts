/**
 * Workflow step contracts and validation.
 */

export type WorkflowStepType = 'agent' | 'tool' | 'approval';

export interface WorkflowStep {
  id: string;
  type: WorkflowStepType;
  assignee: string;
  inputs?: Record<string, unknown>;
  outputs?: readonly string[];
}

export function isWorkflowStepType(value: unknown): value is WorkflowStepType {
  return value === 'agent' || value === 'tool' || value === 'approval';
}
