/**
 * Aggregate design tokens. Re-exports the semantic token groups.
 */

import { colors } from '../colors';
import { typography } from '../typography';
import { radii } from '../spacing';

export const tokens = {
  color: colors,
  font: typography.fontFamily,
  radius: radii,
} as const;

export type DesignTokens = typeof tokens;
