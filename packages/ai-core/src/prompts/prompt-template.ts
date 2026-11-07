/**
 * Small mustache-like prompt template renderer.
 */

export class PromptTemplate {
  readonly template: string;

  constructor(template: string) {
    this.template = template;
  }

  render(variables: Record<string, unknown>): string {
    return this.template.replace(/\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}/g, (_match, key: string) => {
      const value = key.split('.').reduce<unknown>((current, part) => {
        if (current && typeof current === 'object') {
          return (current as Record<string, unknown>)[part];
        }
        return undefined;
      }, variables);
      return value === undefined || value === null ? '' : String(value);
    });
  }

  variables(): string[] {
    const names = new Set<string>();
    for (const match of this.template.matchAll(/\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}/g)) {
      names.add(match[1] ?? '');
    }
    return [...names];
  }
}
