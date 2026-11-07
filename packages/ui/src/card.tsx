import type { HTMLAttributes, ReactNode } from 'react';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function Card({ className = '', children, ...divProps }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-slate-200/90 bg-white shadow-2xs ${className}`}
      {...divProps}
    >
      {children}
    </div>
  );
}
