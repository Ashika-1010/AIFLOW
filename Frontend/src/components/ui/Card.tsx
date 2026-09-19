import React, { type ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  variant?: 'default' | 'nested' | 'amber' | 'accent';
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  variant = 'default',
  onClick
}) => {
  let variantClasses = 'bg-surface border-border';
  if (variant === 'nested') {
    variantClasses = 'bg-surface2 border-border';
  } else if (variant === 'amber') {
    variantClasses = 'bg-surface border-warn/40 shadow-[0_0_20px_rgba(245,158,11,0.06)]';
  } else if (variant === 'accent') {
    variantClasses = 'bg-surface border-accent/40 shadow-[0_0_20px_rgba(255,45,120,0.08)]';
  }

  return (
    <div
      onClick={onClick}
      className={`border rounded-xl p-6 transition-all duration-200 ${variantClasses} ${onClick ? 'cursor-pointer hover:border-border2' : ''} ${className}`}
    >
      {children}
    </div>
  );
};
