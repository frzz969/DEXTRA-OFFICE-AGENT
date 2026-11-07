export type ProgressTone = 'indigo' | 'emerald' | 'amber' | 'rose';

const toneStyles: Record<ProgressTone, string> = {
  indigo: 'bg-indigo-600',
  emerald: 'bg-emerald-500',
  amber: 'bg-amber-500',
  rose: 'bg-rose-500',
};

export interface ProgressBarProps {
  value: number;
  tone?: ProgressTone;
  className?: string;
}

export function ProgressBar({ value, tone = 'indigo', className = '' }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  return (
    <div
      className={`h-1.5 w-full overflow-hidden rounded-full bg-slate-100 ${className}`}
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={`h-full rounded-full transition-all ${toneStyles[tone]}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
