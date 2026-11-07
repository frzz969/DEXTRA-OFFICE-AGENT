/**
 * Workflow definition parsing and validation.
 */

import type { WorkflowTrigger } from '../triggers';
import { isWorkflowStepType, type WorkflowStep } from '../steps';

export type { WorkflowTrigger } from '../triggers';
export type { WorkflowStep, WorkflowStepType } from '../steps';

export interface WorkflowDefinition {
  id: string;
  name: string;
  version: string;
  steps: readonly WorkflowStep[];
  triggers: readonly WorkflowTrigger[];
}

export function parseWorkflowDefinition(raw: unknown): WorkflowDefinition {
  if (!raw || typeof raw !== 'object') throw new Error('Workflow definition must be an object');
  const record = raw as Record<string, unknown>;
  if (typeof record.id !== 'string' || !record.id) throw new Error('Workflow id is required');
  if (typeof record.name !== 'string' || !record.name) throw new Error('Workflow name is required');
  if (typeof record.version !== 'string' || !record.version) throw new Error('Workflow version is required');
  if (!Array.isArray(record.steps) || record.steps.length === 0) throw new Error('Workflow steps must be a non-empty array');

  const steps: WorkflowStep[] = record.steps.map((step, index) => {
    if (!step || typeof step !== 'object') throw new Error(`Step ${index} must be an object`);
    const item = step as Record<string, unknown>;
    if (typeof item.id !== 'string' || !item.id) throw new Error(`Step ${index} id is required`);
    if (!isWorkflowStepType(item.type)) throw new Error(`Step ${item.id} has invalid type`);
    if (typeof item.assignee !== 'string' || !item.assignee) throw new Error(`Step ${item.id} assignee is required`);
    return {
      id: item.id,
      type: item.type,
      assignee: item.assignee,
      inputs: isRecord(item.inputs) ? item.inputs : undefined,
      outputs: Array.isArray(item.outputs) ? item.outputs.map(String) : undefined,
    };
  });

  const triggers: WorkflowTrigger[] = Array.isArray(record.triggers)
    ? record.triggers.map((trigger, index) => {
        if (!trigger || typeof trigger !== 'object') throw new Error(`Trigger ${index} must be an object`);
        const item = trigger as Record<string, unknown>;
        if (item.type !== 'event' && item.type !== 'schedule' && item.type !== 'manual') {
          throw new Error(`Trigger ${index} has invalid type`);
        }
        return {
          type: item.type,
          event: typeof item.event === 'string' ? item.event : undefined,
          cron: typeof item.cron === 'string' ? item.cron : undefined,
          description: typeof item.description === 'string' ? item.description : undefined,
        };
      })
    : [];

  return { id: record.id, name: record.name, version: record.version, steps, triggers };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}
