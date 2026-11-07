import type { ReactNode } from 'react';

export type StatAccent = 'slate' | 'indigo' | 'emerald' | 'amber' | 'rose' | 'blue';

const accentStyles: Record<
  StatAccent,
  { container: string; label: string; icon: string; value: string; hint: string }
> = {
  slate: {
    container: 'border-slate-200/90 bg-white',
    label: 'text-slate-500',
    icon: 'text-slate-400',
    value: 'text-slate-900',
    hint: 'text-slate-500',
  },
  indigo: {
    container: 'border-slate-200/90 bg-white',
    label: 'text-slate-500',
    icon: 'text-indigo-500',
    value: 'text-slate-900',
    hint: 'text-slate-500',
  },
  emerald: {
    container: 'border-emerald-200/80 bg-emerald-50/20',
    label: 'text-emerald-800',
    icon: 'text-emerald-600',
    value: 'text-emerald-900',
    hint: 'text-emerald-700',
  },
  amber: {
    container: 'border-amber-200/90 bg-amber-50/20',
    label: 'text-amber-800',
    icon: 'text-amber-600',
    value: 'text-amber-900',
    hint: 'text-amber-700',
  },
  rose: {
    container: 'border-rose-200/80 bg-rose-50/20',
    label: 'text-rose-800',
    icon: 'text-rose-600',
    value: 'text-rose-900',
    hint: 'text-rose-700',
  },
  blue: {
    container: 'border-blue-200/80 bg-blue-50/20',
    label: 'text-blue-800',
    icon: 'text-blue-600',
    value: 'text-blue-900',
    hint: 'text-blue-700',
  },
};

export interface StatCardProps {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
  accent?: StatAccent;
  className?: string;
}

export function StatCard({
  label,
  value,
  hint,
  icon,
  accent = 'slate',
  className = '',
}: StatCardProps) {
  const styles = accentStyles[accent];
  return (
    <div className={`rounded-xl border p-4 shadow-2xs ${styles.container} ${className}`}>
      <div className="flex items-center justify-between">
        <span
          className={`text-[11px] font-semibold uppercase tracking-wider ${styles.label}`}
        >
          {label}
        </span>
        {icon ? <span className={styles.icon}>{icon}</span> : null}
      </div>
      <div className={`mt-2 flex items-baseline gap-1.5 ${styles.value}`}>{value}</div>
      {hint ? (
        <span className={`mt-1 block text-[11px] font-medium ${styles.hint}`}>{hint}</span>
      ) : null}
    </div>
  );
}
