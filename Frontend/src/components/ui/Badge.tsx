import React, { type ReactNode } from 'react';
import type { Pathway } from '../../mock/types';
import { getPathwayConfig } from '../../lib/colors';

type BadgeVariant = Pathway | 'ok' | 'warn' | 'danger' | 'neutral' | 'verified' | 'escalated';

interface BadgeProps {
  variant?: BadgeVariant;
  children?: ReactNode;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  children,
  className = '',
  size = 'md'
}) => {
  let styleClasses = 'bg-surface2 text-muted border-border';
  let defaultLabel = children;

  if (variant in { deterministic: 1, cache: 1, retrieval: 1, small_model: 1, large_model: 1, escalated: 1 }) {
    const config = getPathwayConfig(variant as Pathway);
    styleClasses = config.pillBg;
    if (!children) defaultLabel = config.badgeLabel;
  } else if (variant === 'ok' || variant === 'verified') {
    styleClasses = 'bg-ok/15 text-ok border-ok/30';
    if (!children) defaultLabel = '✓ Verified';
  } else if (variant === 'warn') {
    styleClasses = 'bg-warn/15 text-warn border-warn/30';
  } else if (variant === 'danger' || variant === 'escalated') {
    styleClasses = 'bg-danger/15 text-danger border-danger/30';
    if (!children) defaultLabel = '✗ Escalated';
  }

  const sizeClasses =
    size === 'sm'
      ? 'text-[10px] px-2 py-0.5'
      : size === 'lg'
      ? 'text-xs px-3 py-1 font-bold'
      : 'text-[11px] px-2.5 py-0.5 font-semibold';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono uppercase tracking-wider rounded border ${styleClasses} ${sizeClasses} ${className}`}
    >
      {children || defaultLabel}
    </span>
  );
};
