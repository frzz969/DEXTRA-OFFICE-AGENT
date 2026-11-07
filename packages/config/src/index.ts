/**
 * `@dextra/config` — shared configuration constants and preset notes.
 */

export * from './ports';
export * from './env-schema';

export const CONFIG_PACKAGE = '@dextra/config' as const;

export const PRESET_NOTES = {
  eslint: 'Shared flat ESLint config planned for `packages/config/eslint`.',
  typescript: 'All packages extend the root `tsconfig.base.json`.',
  tailwind: 'Tailwind v4 theme tokens are owned by `packages/design-system`.',
} as const;
