export type AvatarSize = 'sm' | 'md' | 'lg';

const sizeStyles: Record<AvatarSize, string> = {
  sm: 'w-8 h-8 text-[11px]',
  md: 'w-10 h-10 text-xs',
  lg: 'w-14 h-14 text-base',
};

export interface AvatarProps {
  src?: string;
  name: string;
  size?: AvatarSize;
  className?: string;
}

function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0))
    .join('')
    .slice(0, 2)
    .toUpperCase();
}

export function Avatar({ src, name, size = 'md', className = '' }: AvatarProps) {
  const sizeClass = sizeStyles[size];

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        referrerPolicy="no-referrer"
        className={`shrink-0 rounded-lg border border-slate-200 object-cover ${sizeClass} ${className}`}
      />
    );
  }

  return (
    <span
      aria-label={name}
      className={`inline-flex shrink-0 items-center justify-center rounded-lg border border-indigo-200 bg-indigo-100 font-bold text-indigo-700 ${sizeClass} ${className}`}
    >
      {initials(name)}
    </span>
  );
}
