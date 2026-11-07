/**
 * Template condition and input resolution helpers.
 */

export function resolveTemplate(value: unknown, context: Record<string, unknown>): unknown {
  if (typeof value === 'string') {
    const match = value.match(/^\{\{\s*(.+?)\s*\}\}$/);
    if (match && match[1] !== undefined) return lookup(match[1], context);
    return value.replace(/\{\{\s*(.+?)\s*\}\}/g, (_m, key) => {
      const resolved = lookup(key, context);
      return resolved === undefined || resolved === null ? '' : String(resolved);
    });
  }
  if (Array.isArray(value)) return value.map((item) => resolveTemplate(item, context));
  if (value && typeof value === 'object') {
    const result: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      result[key] = resolveTemplate(item, context);
    }
    return result;
  }
  return value;
}

function lookup(path: string, context: Record<string, unknown>): unknown {
  return path.split('.').reduce<unknown>((current, part) => {
    if (current && typeof current === 'object') {
      return (current as Record<string, unknown>)[part];
    }
    return undefined;
  }, context);
}
