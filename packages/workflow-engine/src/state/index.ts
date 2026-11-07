/**
 * Workflow run state and in-memory store.
 */

export type WorkflowRunStatus =
  | 'pending'
  | 'running'
  | 'awaiting_approval'
  | 'completed'
  | 'failed';

export interface WorkflowRun {
  id: string;
  workflowId: string;
  status: WorkflowRunStatus;
  currentStepId?: string;
  startedAt: string;
  finishedAt?: string;
  outputs: Record<string, unknown>;
  error?: string;
}

export class WorkflowRunStore {
  readonly #runs = new Map<string, WorkflowRun>();

  create(run: WorkflowRun): WorkflowRun {
    this.#runs.set(run.id, run);
    return run;
  }

  get(id: string): WorkflowRun | undefined {
    return this.#runs.get(id);
  }

  update(id: string, patch: Partial<WorkflowRun>): WorkflowRun | undefined {
    const current = this.#runs.get(id);
    if (!current) return undefined;
    const next = { ...current, ...patch };
    this.#runs.set(id, next);
    return next;
  }

  list(): readonly WorkflowRun[] {
    return [...this.#runs.values()];
  }
}
