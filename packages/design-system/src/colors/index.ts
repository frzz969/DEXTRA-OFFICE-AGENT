/**
 * Color tokens extracted from `src/styles.css`.
 */

export const colors = {
  surface: '#f8fafc',
  surfaceElevated: '#ffffff',
  surfaceSoft: '#eef2ff',
  ink: '#0f172a',
  brand: '#4f46e5',
  brandHover: '#4338ca',
  brandSoft: '#eef2ff',
  sidebar: '#0b0f19',
  sidebarHover: '#151d2e',
  sidebarBorder: '#1e293b',
  sidebarFooter: '#0e1424',
  success: '#059669',
  successSoft: '#ecfdf5',
  warning: '#f59e0b',
  warningSoft: '#fffbeb',
  danger: '#e11d48',
  dangerSoft: '#fff1f2',
  info: '#2563eb',
  infoSoft: '#eff6ff',
} as const;

export type ColorToken = keyof typeof colors;
