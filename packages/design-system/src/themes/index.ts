/**
 * Theme definitions built from the design tokens.
 */

import { tokens } from '../tokens';

export const lightTheme = tokens;

export const themes = {
  light: lightTheme,
} as const;

export type ThemeName = keyof typeof themes;
