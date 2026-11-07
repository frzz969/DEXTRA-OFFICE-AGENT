#!/usr/bin/env node
/**
 * check-env.mjs — report toolchain versions and presence of key env vars.
 *
 * Deliberately prints only whether a variable is set, never its value, so it
 * is safe to paste the output into an issue.
 */

const REQUIRED = ['DATABASE_URL', 'REDIS_URL', 'AUTH_SECRET'];
const OPTIONAL = [
  'OPENAI_API_KEY',
  'ANTHROPIC_API_KEY',
  'GOOGLE_AI_API_KEY',
  'AI_DEFAULT_PROVIDER',
  'AI_DEFAULT_MODEL',
];

function status(name) {
  return process.env[name] ? 'set' : 'missing';
}

import { execFileSync } from 'node:child_process';

function detectPnpm() {
  const fromAgent = process.env.npm_config_user_agent?.match(/pnpm\/(\S+)/)?.[1];
  if (fromAgent) return fromAgent;
  try {
    return execFileSync('pnpm', ['--version'], { encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

const pnpmVersion = detectPnpm();

console.log('DEXTRA environment check');
console.log('------------------------');
console.log(`node : ${process.version}`);
console.log(`pnpm : ${pnpmVersion}`);
console.log('');
console.log('Required variables:');
for (const name of REQUIRED) console.log(`  ${name.padEnd(22)} ${status(name)}`);
console.log('');
console.log('Optional variables:');
for (const name of OPTIONAL) console.log(`  ${name.padEnd(22)} ${status(name)}`);
