import React, { type ReactNode } from 'react';

interface SectionLabelProps {
  children: ReactNode;
  variant?: 'accent' | 'muted';
  className?: string;
}

export const SectionLabel: React.FC<SectionLabelProps> = ({
  children,
  variant = 'accent',
  className = ''
}) => {
  const colorClass = variant === 'accent' ? 'text-accent' : 'text-muted';
  return (
    <div className={`font-mono text-[11px] uppercase tracking-[0.18em] ${colorClass} ${className}`}>
      {children}
    </div>
  );
};
