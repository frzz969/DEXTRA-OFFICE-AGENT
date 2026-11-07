/**
 * Incremental Server-Sent Events parser.
 */

export interface SSEEvent {
  event?: string;
  data: string;
  id?: string;
  retry?: number;
}

export class SSEParser {
  #buffer = '';

  feed(chunk: string): SSEEvent[] {
    this.#buffer += chunk;
    const events: SSEEvent[] = [];
    let boundary = this.#buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const raw = this.#buffer.slice(0, boundary);
      this.#buffer = this.#buffer.slice(boundary + 2);
      const event = parseEvent(raw);
      if (event) events.push(event);
      boundary = this.#buffer.indexOf('\n\n');
    }
    return events;
  }

  flush(): SSEEvent[] {
    if (!this.#buffer.trim()) {
      this.#buffer = '';
      return [];
    }
    const event = parseEvent(this.#buffer);
    this.#buffer = '';
    return event ? [event] : [];
  }
}

function parseEvent(raw: string): SSEEvent | undefined {
  const lines = raw.split(/\r?\n/);
  const event: SSEEvent = { data: '' };
  const dataLines: string[] = [];
  let hasField = false;

  for (const line of lines) {
    if (!line || line.startsWith(':')) continue;
    const separator = line.indexOf(':');
    const field = separator === -1 ? line : line.slice(0, separator);
    const value = separator === -1 ? '' : line.slice(separator + 1).replace(/^ /, '');
    hasField = true;
    if (field === 'event') event.event = value;
    else if (field === 'data') dataLines.push(value);
    else if (field === 'id') event.id = value;
    else if (field === 'retry') event.retry = Number(value);
  }

  if (!hasField) return undefined;
  event.data = dataLines.join('\n');
  return event;
}
