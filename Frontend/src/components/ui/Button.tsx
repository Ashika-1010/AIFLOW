import React, { type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'ghost' | 'amber' | 'accent-ghost';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  className?: string;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}) => {
  let variantClasses = '';
  if (variant === 'primary') {
    variantClasses =
      'bg-accent text-white border-transparent shadow-[0_0_18px_rgba(255,45,120,0.35)] hover:shadow-[0_0_28px_rgba(255,45,120,0.55)] hover:bg-[#ff176b] active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none disabled:shadow-none';
  } else if (variant === 'ghost') {
    variantClasses =
      'bg-transparent border border-border text-text hover:border-border2 hover:bg-surface2 hover:text-white active:scale-[0.99] disabled:opacity-40 disabled:pointer-events-none';
  } else if (variant === 'amber') {
    variantClasses =
      'bg-warn/15 border border-warn/40 text-warn hover:bg-warn/25 shadow-[0_0_18px_rgba(245,158,11,0.25)] active:scale-[0.99]';
  } else if (variant === 'accent-ghost') {
    variantClasses =
      'bg-accentBg border border-accent/30 text-accent hover:border-accent hover:bg-accent/15';
  }

  let sizeClasses = '';
  if (size === 'sm') {
    sizeClasses = 'px-3 py-1.5 text-xs rounded-md font-medium';
  } else if (size === 'md') {
    sizeClasses = 'px-4 py-2 text-sm rounded-lg font-medium';
  } else if (size === 'lg') {
    sizeClasses = 'px-6 py-3 text-base rounded-lg font-semibold';
  } else if (size === 'xl') {
    sizeClasses = 'px-8 py-3.5 text-base md:text-lg rounded-xl font-semibold';
  }

  return (
    <button
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center gap-2 border transition-all duration-150 cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-bg ${variantClasses} ${sizeClasses} ${className}`}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-current" />
          <span>{children}</span>
        </>
      ) : (
        <>
          {leftIcon && <span className="shrink-0">{leftIcon}</span>}
          <span>{children}</span>
          {rightIcon && <span className="shrink-0">{rightIcon}</span>}
        </>
      )}
    </button>
  );
};
