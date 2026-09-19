import React from 'react';
import { formatWh, formatPct } from '../lib/format';
import { SectionLabel } from './ui/SectionLabel';
import { useCountUp } from '../lib/useCountUp';

interface BaselineComparisonProps {
  aiflowEnergyWh: number;
  baselineEnergyWh: number;
  className?: string;
}

export const BaselineComparison: React.FC<BaselineComparisonProps> = ({
  aiflowEnergyWh,
  baselineEnergyWh,
  className = ''
}) => {
  const maxWh = Math.max(baselineEnergyWh, aiflowEnergyWh, 0.0001);
  const aiflowPct = Math.max(3, Math.min(100, (aiflowEnergyWh / maxWh) * 100));
  const baselinePct = 100;

  const rawReduction = Math.max(
    0,
    ((baselineEnergyWh - aiflowEnergyWh) / baselineEnergyWh) * 100
  );
  const animatedReduction = useCountUp(Math.round(rawReduction), 600, 0);

  return (
    <div className={`space-y-4 ${className}`}>
      <SectionLabel className="mb-2">BASELINE COMPARISON</SectionLabel>

      {/* Comparison Bars */}
      <div className="space-y-3">
        {/* AIFlow Bar */}
        <div>
          <div className="flex justify-between items-center text-xs font-mono mb-1">
            <span className="text-text font-semibold uppercase text-[11px] tracking-wider">AIFLOW</span>
            <span className="text-accent font-semibold">{formatWh(aiflowEnergyWh)}</span>
          </div>
          <div className="h-3 w-full bg-surface2 rounded-full overflow-hidden border border-border/50">
            <div
              className="h-full bg-accent rounded-full transition-all duration-500 shadow-[0_0_12px_rgba(255,45,120,0.4)]"
              style={{ width: `${aiflowPct}%` }}
            />
          </div>
        </div>

        {/* Baseline Bar */}
        <div>
          <div className="flex justify-between items-center text-xs font-mono mb-1">
            <span className="text-muted font-normal uppercase text-[11px] tracking-wider">ALWAYS-LARGE BASELINE</span>
            <span className="text-muted">{formatWh(baselineEnergyWh)}</span>
          </div>
          <div className="h-3 w-full bg-surface2 rounded-full overflow-hidden border border-border/50">
            <div
              className="h-full bg-muted/40 rounded-full transition-all duration-500"
              style={{ width: `${baselinePct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Green-tinted reduction box */}
      <div className="bg-ok/10 border border-ok/30 rounded-xl p-4 text-center mt-4">
        <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-ok/90 font-semibold mb-1">
          ESTIMATED PATHWAY REDUCTION
        </div>
        <div className="text-3xl md:text-4xl font-mono font-bold text-ok tabular-nums">
          {formatPct(animatedReduction)}
        </div>
      </div>
    </div>
  );
};
