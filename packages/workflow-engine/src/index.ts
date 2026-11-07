/**
 * `@dextra/workflow-engine` — multi-step workflow definitions and runs.
 */

export * from './definitions';
export * from './steps';
export * from './conditions';
export * from './state';
export * from './executor';
export * from './scheduler';
export * from './triggers';

export interface WorkflowEngine {
  start(definition: WorkflowDefinition, input: Record<string, unknown>): Promise<WorkflowRun>;
  getRun(id: string): WorkflowRun | undefined;
}

import type { WorkflowDefinition } from './definitions';
import type { WorkflowRun } from './state';
