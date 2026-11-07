/**
 * Anthropic messages client.
 */

import type { AICompletionRequest, AICompletionResult } from '../models/types';
import type { ProviderConfig } from './provider.interface';
import { requireApiKey } from './provider.interface';

export class AnthropicProvider {
  readonly id = 'anthropic' as const;
  readonly config: ProviderConfig;

  constructor(config: ProviderConfig = {}) {
    this.config = config;
  }

  async complete(request: AICompletionRequest): Promise<AICompletionResult> {
    const apiKey = requireApiKey(this.config, 'anthropic');
    const baseUrl = this.config.baseUrl ?? 'https://api.anthropic.com/v1';
    const system = request.messages
      .filter((message) => message.role === 'system')
      .map((message) => message.content)
      .join('\n\n');
    const messages = request.messages
      .filter((message) => message.role !== 'system')
      .map((message) => ({ role: message.role, content: message.content }));

    const response = await fetch(`${baseUrl}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: request.model.model,
        system: system || undefined,
        messages,
        temperature: request.temperature,
        max_tokens: request.maxTokens ?? 1024,
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Anthropic request failed (${response.status}): ${body}`);
    }

    const data = (await response.json()) as {
      content?: Array<{ type?: string; text?: string }>;
      usage?: { input_tokens?: number; output_tokens?: number };
      model?: string;
    };

    const content = (data.content ?? [])
      .filter((part) => part.type === 'text')
      .map((part) => part.text ?? '')
      .join('');

    return {
      content,
      provider: 'anthropic',
      model: data.model ?? request.model.model,
      usage: data.usage
        ? {
            promptTokens: data.usage.input_tokens ?? 0,
            completionTokens: data.usage.output_tokens ?? 0,
          }
        : undefined,
    };
  }
}
