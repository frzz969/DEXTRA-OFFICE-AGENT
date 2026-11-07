/**
 * Environment reader with small validators.
 */

export type EnvValue = string | undefined;

export interface EnvReaderOptions {
  required?: boolean;
  defaultValue?: string;
  validate?: (value: string) => boolean;
}

export function readEnv(name: string, options: EnvReaderOptions = {}): string | undefined {
  const value = process.env[name];
  if (value === undefined || value === '') {
    if (options.required && options.defaultValue === undefined) {
      throw new Error(`Missing required environment variable: ${name}`);
    }
    return options.defaultValue;
  }
  if (options.validate && !options.validate(value)) {
    throw new Error(`Invalid environment variable: ${name}`);
  }
  return value;
}

export function requireEnv(name: string, validate?: (value: string) => boolean): string {
  return readEnv(name, { required: true, validate }) as string;
}

export function readNumberEnv(name: string, defaultValue?: number): number | undefined {
  const raw = readEnv(name);
  if (raw === undefined) return defaultValue;
  const value = Number(raw);
  if (!Number.isFinite(value)) throw new Error(`Environment variable ${name} must be a number`);
  return value;
}

export function readBooleanEnv(name: string, defaultValue = false): boolean {
  const raw = readEnv(name);
  if (raw === undefined) return defaultValue;
  return raw === 'true' || raw === '1';
}
