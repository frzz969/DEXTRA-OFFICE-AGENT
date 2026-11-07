/**
 * Spacing, radius and elevation tokens extracted from `src/styles.css`.
 */

export const radii = {
  card: '12px',
  control: '8px',
} as const;

export const shadows = {
  card: '0 1px 1px rgb(15 23 42 / 0.04)',
  modal: '0 24px 48px -12px rgb(15 23 42 / 0.25)',
} as const;

export const spacing = {
  0: '0px',
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  6: '24px',
  8: '32px',
} as const;

export type RadiusToken = keyof typeof radii;
export type ShadowToken = keyof typeof shadows;
