import React from 'react';
import type { EnergyBand } from '../../mock/types';
import { formatWh } from '../../lib/format';

interface RangeBarProps {
  energy: EnergyBand;
  className?: string;
  maxVal?: number; // optional baseline to scale against
}

export const RangeBar: React.FC<RangeBarProps> = ({
  energy,
  className = '',
  maxVal
}) => {
  // Use high bound or maxVal as the 100% width reference
  const reference = maxVal || (energy.high > 0 ? energy.high : 0.0001);
  
  // Calculate relative widths with minimum visible bar width of 3%
  const lowWidthPct = Math.max(3, Math.min(100, (energy.low / reference) * 100));
  const centralWidthPct = Math.max(4, Math.min(100, (energy.central / reference) * 100));
  const highWidthPct = Math.max(5, Math.min(100, (energy.high / reference) * 100));

  return (
    <div className={`space-y-4 ${className}`}>
      {/* LOW */}
      <div className="space-y-1.5">
        <div className="flex justify-between items-center text-xs font-mono">
          <span className="text-muted tracking-wider uppercase text-[11px]">LOW</span>
          <span className="text-text font-medium">{formatWh(energy.low)}</span>
        </div>
        <div className="h-2.5 w-full bg-surface2 rounded-full overflow-hidden border border-border/50">
          <div
            className="h-full bg-purple-500/80 rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(168,85,247,0.3)]"
            style={{ width: `${lowWidthPct}%` }}
          />
        </div>
      </div>

      {/* CENTRAL ESTIMATE */}
      <div className="space-y-1.5">
        <div className="flex justify-between items-center text-xs font-mono">
          <span className="text-muted tracking-wider uppercase text-[11px]">CENTRAL ESTIMATE</span>
          <span className="text-accent font-semibold">{formatWh(energy.central)}</span>
        </div>
        <div className="h-2.5 w-full bg-surface2 rounded-full overflow-hidden border border-border/50">
          <div
            className="h-full bg-accent rounded-full transition-all duration-500 shadow-[0_0_10px_rgba(255,45,120,0.4)]"
            style={{ width: `${centralWidthPct}%` }}
          />
        </div>
      </div>

      {/* HIGH */}
      <div className="space-y-1.5">
        <div className="flex justify-between items-center text-xs font-mono">
          <span className="text-muted tracking-wider uppercase text-[11px]">HIGH</span>
          <span className="text-warn font-medium">{formatWh(energy.high)}</span>
        </div>
        <div className="h-2.5 w-full bg-surface2 rounded-full overflow-hidden border border-border/50">
          <div
            className="h-full bg-warn rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(245,158,11,0.3)]"
            style={{ width: `${highWidthPct}%` }}
          />
        </div>
      </div>
    </div>
  );
};
