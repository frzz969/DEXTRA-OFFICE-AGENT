/**
 * `@dextra/agent-runtime` — executes a single agent run.
 *
 * Runtime is responsible for loading an agent, checking governance, invoking
 * tools, and emitting audit events. No execution engine is implemented yet.
 */

export type AgentRunStatus = 'succeeded' | 'failed' | 'requires_approval';

export interface AgentExecutionContext {
  runId: string;
  agentId: string;
  /** Opaque task inputs supplied by the orchestrator. */
  inputs: Record<string, unknown>;
  /** Correlates related runs (e.g. one WorkBuddy session). */
  traceId?: string;
}

export interface AgentRunResult {
  runId: string;
  status: AgentRunStatus;
  output?: unknown;
  error?: string;
}

export interface AgentRunner {
  run(context: AgentExecutionContext): Promise<AgentRunResult>;
}

export interface AgentRuntimeOptions {
  maxConcurrentRuns?: number;
}

/**
 * TODO(agent-runtime): implement governance gate → tool execution → audit
 * pipeline. Every run must pass through `@dextra/governance`; there is no
 * bypass. Do not fake executions in this package.
 */
export interface AgentRuntime {
  readonly options: AgentRuntimeOptions;
  execute(runner: AgentRunner, context: AgentExecutionContext): Promise<AgentRunResult>;
}
