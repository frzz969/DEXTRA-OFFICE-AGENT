/**
 * `@dextra/agent-registry` — catalogue of available agents and their tools.
 *
 * The in-memory registry below is a real (if minimal) implementation suitable
 * for tests and local wiring. Persistent registration lives in the backend.
 */

export type AgentStatus = 'online' | 'busy' | 'idle' | 'offline';

export interface AgentDescriptor {
  id: string;
  name: string;
  department: string;
  role: string;
  status: AgentStatus;
  /** Tool identifiers the agent is allowed to use. */
  tools: readonly string[];
}

export interface AgentRegistry {
  register(agent: AgentDescriptor): void;
  get(id: string): AgentDescriptor | undefined;
  list(): readonly AgentDescriptor[];
  unregister(id: string): boolean;
}

export class InMemoryAgentRegistry implements AgentRegistry {
  readonly #agents = new Map<string, AgentDescriptor>();

  register(agent: AgentDescriptor): void {
    this.#agents.set(agent.id, agent);
  }

  get(id: string): AgentDescriptor | undefined {
    return this.#agents.get(id);
  }

  list(): readonly AgentDescriptor[] {
    return [...this.#agents.values()];
  }

  unregister(id: string): boolean {
    return this.#agents.delete(id);
  }
}

/** TODO(agent-registry): sync with backend registry and validate tool grants. */
