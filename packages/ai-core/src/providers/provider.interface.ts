/**
 * Shared provider contract and configuration.
 */

import type { AICompletionRequest, AICompletionResult, AIProvider, AIProviderAdapter } from '../models/types';

export type { AICompletionRequest, AICompletionResult, AIProvider, AIProviderAdapter };

export interface ProviderConfig {
  apiKey?: string;
  baseUrl?: string;
  defaultModel?: string;
}

export interface Provider extends AIProviderAdapter {
  readonly config: ProviderConfig;
  complete(request: AICompletionRequest): Promise<AICompletionResult>;
}

export function requireApiKey(config: ProviderConfig, provider: AIProvider): string {
  if (!config.apiKey) {
    throw new Error(`${provider} API key is required`);
  }
  return config.apiKey;
}
