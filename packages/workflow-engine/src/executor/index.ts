/**
 * Sequential workflow executor with an approval gate callback.
 */

import { randomUUID } from 'node:crypto';
import type { WorkflowDefinition, WorkflowStep } from '../definitions';
import { resolveTemplate } from '../conditions';
import { WorkflowRunStore, type WorkflowRun, type WorkflowRunStatus } from '../state';

export type ApprovalGate = (step: WorkflowStep, run: WorkflowRun) => Promise<boolean> | boolean;

export interface StepHandler {
  (step: WorkflowStep, inputs: Record<string, unknown>): Promise<unknown> | unknown;
}

export class WorkflowExecutor {
  readonly #store = new WorkflowRunStore();
  readonly #approvalGate: ApprovalGate;
  readonly #handlers: Map<string, StepHandler>;

  constructor(options: { approvalGate?: ApprovalGate; handlers?: Record<string, StepHandler> } = {}) {
    this.#approvalGate = options.approvalGate ?? (async () => true);
    this.#handlers = new Map(Object.entries(options.handlers ?? {}));
  }

  getRun(id: string): WorkflowRun | undefined {
    return this.#store.get(id);
  }

  async start(definition: WorkflowDefinition, input: Record<string, unknown> = {}): Promise<WorkflowRun> {
    const run: WorkflowRun = {
      id: randomUUID(),
      workflowId: definition.id,
      status: 'running',
      startedAt: new Date().toISOString(),
      outputs: { ...input },
    };
    this.#store.create(run);

    const stepOutputs: Record<string, Record<string, unknown>> = {};
    try {
      for (const step of definition.steps) {
        this.#store.update(run.id, { currentStepId: step.id, status: 'running' });
        const context = { event: input, steps: stepOutputs, input };
        const resolvedInputs = resolveTemplate(step.inputs ?? {}, context) as Record<string, unknown>;

        if (step.type === 'approval') {
          const approved = await this.#approvalGate(step, run);
          if (!approved) {
            const failed = this.#store.update(run.id, {
              status: 'failed',
              error: `Approval rejected at ${step.id}`,
              finishedAt: new Date().toISOString(),
            });
            return failed as WorkflowRun;
          }
          stepOutputs[step.id] = { approvalDecision: 'approved', ...resolvedInputs };
          continue;
        }

        const handler = this.#handlers.get(step.assignee);
        const result = handler ? await handler(step, resolvedInputs) : { ok: true, step: step.id };
        const output: Record<string, unknown> = { ...(resolvedInputs ?? {}) };
        for (const key of step.outputs ?? []) output[key] = result;
        stepOutputs[step.id] = output;
        const current = this.#store.get(run.id)!;
        this.#store.update(run.id, { outputs: { ...current.outputs, ...output } });
      }

      const completed = this.#store.update(run.id, {
        status: 'completed',
        currentStepId: undefined,
        finishedAt: new Date().toISOString(),
      });
      return completed as WorkflowRun;
    } catch (error) {
      const failed = this.#store.update(run.id, {
        status: 'failed',
        error: error instanceof Error ? error.message : String(error),
        finishedAt: new Date().toISOString(),
      });
      return failed as WorkflowRun;
    }
  }
}
