/**
 * OpenAI-compatible chat completions client.
 */

import type { AICompletionRequest, AICompletionResult } from '../models/types';
import type { ProviderConfig } from './provider.interface';
import { requireApiKey } from './provider.interface';

export class OpenAIProvider {
  readonly id = 'openai' as const;
  readonly config: ProviderConfig;

  constructor(config: ProviderConfig = {}) {
    this.config = config;
  }

  async complete(request: AICompletionRequest): Promise<AICompletionResult> {
    const apiKey = requireApiKey(this.config, 'openai');
    const baseUrl = this.config.baseUrl ?? 'https://api.openai.com/v1';
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: request.model.model,
        messages: request.messages,
        temperature: request.temperature,
        max_tokens: request.maxTokens,
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`OpenAI request failed (${response.status}): ${body}`);
    }

    const data = (await response.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
      usage?: { prompt_tokens?: number; completion_tokens?: number };
      model?: string;
    };

    const content = data.choices?.[0]?.message?.content ?? '';
    return {
      content,
      provider: 'openai',
      model: data.model ?? request.model.model,
      usage: data.usage
        ? {
            promptTokens: data.usage.prompt_tokens ?? 0,
            completionTokens: data.usage.completion_tokens ?? 0,
          }
        : undefined,
    };
  }
}
