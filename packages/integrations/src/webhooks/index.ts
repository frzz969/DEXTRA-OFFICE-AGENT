/**
 * Fetch-based webhook sender.
 */

export interface WebhookPayload {
  event: string;
  data: Record<string, unknown>;
  timestamp?: string;
}

export interface WebhookSenderOptions {
  url: string;
  secret?: string;
  timeoutMs?: number;
}

export async function sendWebhook(options: WebhookSenderOptions, payload: WebhookPayload): Promise<{ status: number }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs ?? 10000);
  try {
    const response = await fetch(options.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(options.secret ? { 'X-Webhook-Secret': options.secret } : {}),
      },
      body: JSON.stringify({ ...payload, timestamp: payload.timestamp ?? new Date().toISOString() }),
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Webhook delivery failed (${response.status}): ${body}`);
    }
    return { status: response.status };
  } finally {
    clearTimeout(timer);
  }
}
