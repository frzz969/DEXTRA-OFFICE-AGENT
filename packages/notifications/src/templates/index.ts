/**
 * Notification template rendering.
 */

export interface NotificationTemplate {
  id: string;
  subject: string;
  body: string;
}

export function renderTemplate(template: string, variables: Record<string, unknown>): string {
  return template.replace(/\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}/g, (_match, key: string) => {
    const value = key.split('.').reduce<unknown>((current, part) => {
      if (current && typeof current === 'object') return (current as Record<string, unknown>)[part];
      return undefined;
    }, variables);
    return value === undefined || value === null ? '' : String(value);
  });
}

export function renderNotification(template: NotificationTemplate, variables: Record<string, unknown>) {
  return {
    subject: renderTemplate(template.subject, variables),
    body: renderTemplate(template.body, variables),
  };
}
