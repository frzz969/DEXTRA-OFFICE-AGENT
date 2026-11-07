import type { ReactNode } from 'react';

export interface EmptyStateProps {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, className = '' }: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-200 bg-slate-50/50 px-6 py-10 text-center ${className}`}
    >
      {icon ? <div className="text-slate-400">{icon}</div> : null}
      <p className="text-sm font-semibold text-slate-800">{title}</p>
      {description ? (
        <p className="max-w-sm text-xs leading-relaxed text-slate-500">{description}</p>
      ) : null}
    </div>
  );
}
