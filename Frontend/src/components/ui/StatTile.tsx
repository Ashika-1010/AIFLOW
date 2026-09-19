import React, { type ReactNode } from 'react';
import { SectionLabel } from './SectionLabel';

interface StatTileProps {
  label: string;
  value: ReactNode;
  sublabel?: string;
  delta?: string;
  deltaType?: 'positive' | 'negative' | 'neutral' | 'accent' | 'warn';
  tooltip?: string;
  size?: 'normal' | 'large' | 'compact';
  color?: 'default' | 'accent' | 'green' | 'amber' | 'red';
  className?: string;
}

export const StatTile: React.FC<StatTileProps> = ({
  label,
  value,
  sublabel,
  delta,
  deltaType = 'neutral',
  tooltip,
  size = 'normal',
  color = 'default',
  className = ''
}) => {
  let valueColor = 'text-text';
  if (color === 'accent') valueColor = 'text-accent';
  else if (color === 'green') valueColor = 'text-ok';
  else if (color === 'amber') valueColor = 'text-warn';
  else if (color === 'red') valueColor = 'text-danger';

  let textSize = 'text-2xl md:text-3xl';
  if (size === 'large') textSize = 'text-3xl md:text-4xl';
  if (size === 'compact') textSize = 'text-xl';

  return (
    <div
      title={tooltip}
      className={`bg-surface2/60 border border-border rounded-lg p-4 flex flex-col justify-between transition-colors ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <SectionLabel variant="muted">{label}</SectionLabel>
        {delta && (
          <span
            className={`text-xs font-mono font-medium px-1.5 py-0.5 rounded ${
              deltaType === 'positive'
                ? 'text-ok bg-ok/10 border border-ok/30'
                : deltaType === 'warn'
                ? 'text-warn bg-warn/10 border border-warn/30'
                : deltaType === 'accent'
                ? 'text-accent bg-accent/10 border border-accent/30'
                : deltaType === 'negative'
                ? 'text-danger bg-danger/10 border border-danger/30'
                : 'text-muted bg-surface2 border border-border'
            }`}
          >
            {delta}
          </span>
        )}
      </div>
      <div>
        <div className={`font-mono font-semibold tracking-tight ${textSize} ${valueColor} tabular-nums`}>
          {value}
        </div>
        {sublabel && (
          <div className="text-xs text-muted mt-1 font-sans">
            {sublabel}
          </div>
        )}
      </div>
    </div>
  );
};
