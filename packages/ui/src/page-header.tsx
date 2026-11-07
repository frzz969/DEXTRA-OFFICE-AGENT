import type { ReactNode } from 'react';

export interface PageHeaderProps {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  icon,
  actions,
  className = '',
}: PageHeaderProps) {
  return (
    <div
      className={`flex flex-col gap-4 md:flex-row md:items-center md:justify-between ${className}`}
    >
      <div className="min-w-0">
        {eyebrow ? (
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold text-indigo-600">
            {icon}
            <span>{eyebrow}</span>
          </div>
        ) : null}
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 lg:text-3xl">
          {title}
        </h1>
        {description ? (
          <p className="mt-0.5 text-sm text-slate-500">{description}</p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 items-center gap-2.5">{actions}</div>
      ) : null}
    </div>
  );
}
