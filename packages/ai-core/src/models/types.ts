/**
 * Provider-agnostic AI model and completion types.
 */

export type AIProvider = 'openai' | 'anthropic' | 'google' | 'local' | 'custom';

export interface ModelDescriptor {
  provider: AIProvider;
  /** Provider-specific model id, e.g. `gpt-4.1-mini`. */
  model: string;
  contextWindow?: number;
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface AICompletionRequest {
  model: ModelDescriptor;
  messages: readonly ChatMessage[];
  temperature?: number;
  maxTokens?: number;
}

export interface AICompletionResult {
  content: string;
  usage?: { promptTokens: number; completionTokens: number };
  provider: AIProvider;
  model: string;
}

/** Adapter implemented per provider. */
export interface AIProviderAdapter {
  readonly id: AIProvider;
  complete(request: AICompletionRequest): Promise<AICompletionResult>;
}

export interface AIClient {
  complete(request: AICompletionRequest): Promise<AICompletionResult>;
}
