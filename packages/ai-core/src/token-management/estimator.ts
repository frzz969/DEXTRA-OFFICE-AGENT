/**
 * Lightweight token estimator for budgeting prompts.
 */

export function estimateTokens(text: string): number {
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

export function estimateMessages(messages: readonly { content: string }[]): number {
  return messages.reduce((total, message) => total + estimateTokens(message.content) + 4, 0);
}
