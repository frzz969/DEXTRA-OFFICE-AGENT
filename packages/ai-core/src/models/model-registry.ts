/**
 * In-memory registry of available AI models.
 */

import type { AIProvider, ModelDescriptor } from './types';

export interface ModelRecord extends ModelDescriptor {
  displayName?: string;
  enabled?: boolean;
}

export class ModelRegistry {
  readonly #models = new Map<string, ModelRecord>();

  register(model: ModelRecord): void {
    this.#models.set(`${model.provider}:${model.model}`, model);
  }

  get(provider: AIProvider, model: string): ModelRecord | undefined {
    return this.#models.get(`${provider}:${model}`);
  }

  list(): readonly ModelRecord[] {
    return [...this.#models.values()];
  }

  listByProvider(provider: AIProvider): readonly ModelRecord[] {
    return this.list().filter((model) => model.provider === provider);
  }

  unregister(provider: AIProvider, model: string): boolean {
    return this.#models.delete(`${provider}:${model}`);
  }
}
