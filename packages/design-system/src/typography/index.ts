/**
 * Typography tokens extracted from `src/styles.css`.
 */

export const fontFamily = {
  sans: "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace",
} as const;

export const typography = {
  fontFamily,
} as const;

export type FontFamilyToken = keyof typeof fontFamily;
