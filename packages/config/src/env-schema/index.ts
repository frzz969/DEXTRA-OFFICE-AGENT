/**
 * Plain environment schema validators.
 */

export interface EnvSchemaField {
  name: string;
  required?: boolean;
  description?: string;
  validate?: (value: string) => boolean;
}

export const ENV_SCHEMA: readonly EnvSchemaField[] = [
  { name: 'DEXTRA_API_URL', required: false, description: 'Base URL for the DEXTRA API' },
  { name: 'OPENAI_API_KEY', required: false, description: 'OpenAI API key' },
  { name: 'ANTHROPIC_API_KEY', required: false, description: 'Anthropic API key' },
  { name: 'GOOGLE_AI_API_KEY', required: false, description: 'Google AI API key' },
];

export function validateEnv(values: Record<string, string | undefined>): string[] {
  const errors: string[] = [];
  for (const field of ENV_SCHEMA) {
    const value = values[field.name];
    if (field.required && !value) errors.push(`Missing ${field.name}`);
    if (value && field.validate && !field.validate(value)) errors.push(`Invalid ${field.name}`);
  }
  return errors;
}
