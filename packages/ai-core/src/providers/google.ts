/**
 * Google Gemini generateContent client.
 */

import type { AICompletionRequest, AICompletionResult } from '../models/types';
import type { ProviderConfig } from './provider.interface';
import { requireApiKey } from './provider.interface';

export class GoogleProvider {
  readonly id = 'google' as const;
  readonly config: ProviderConfig;

  constructor(config: ProviderConfig = {}) {
    this.config = config;
  }

  async complete(request: AICompletionRequest): Promise<AICompletionResult> {
    const apiKey = requireApiKey(this.config, 'google');
    const baseUrl = this.config.baseUrl ?? 'https://generativelanguage.googleapis.com/v1beta';
    const system = request.messages
      .filter((message) => message.role === 'system')
      .map((message) => message.content)
      .join('\n\n');
    const contents = request.messages
      .filter((message) => message.role !== 'system')
      .map((message) => ({
        role: message.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: message.content }],
      }));

    const response = await fetch(
      `${baseUrl}/models/${encodeURIComponent(request.model.model)}:generateContent?key=${encodeURIComponent(apiKey)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents,
          systemInstruction: system ? { parts: [{ text: system }] } : undefined,
          generationConfig: {
            temperature: request.temperature,
            maxOutputTokens: request.maxTokens,
          },
        }),
      },
    );

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Google request failed (${response.status}): ${body}`);
    }

    const data = (await response.json()) as {
      candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
      usageMetadata?: { promptTokenCount?: number; candidatesTokenCount?: number };
      modelVersion?: string;
    };

    const content =
      data.candidates?.[0]?.content?.parts?.map((part) => part.text ?? '').join('') ?? '';

    return {
      content,
      provider: 'google',
      model: data.modelVersion ?? request.model.model,
      usage: data.usageMetadata
        ? {
            promptTokens: data.usageMetadata.promptTokenCount ?? 0,
            completionTokens: data.usageMetadata.candidatesTokenCount ?? 0,
          }
        : undefined,
    };
  }
}
