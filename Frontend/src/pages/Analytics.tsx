import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { getAnalytics } from '../mock/api';
import type { AnalyticsPayload } from '../mock/types';
import { Card } from '../components/ui/Card';
import { SectionLabel } from '../components/ui/SectionLabel';
import { StatTile } from '../components/ui/StatTile';
import { Skeleton } from '../components/ui/Skeleton';
import { formatWh, formatPct } from '../lib/format';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
  Cell
} from 'recharts';

export const Analytics: React.FC = () => {
  const { pessimistic } = useApp();
  const [data, setData] = useState<AnalyticsPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    setLoading(true);
    getAnalytics(pessimistic)
      .then(setData)
      .finally(() => setLoading(false));
  }, [pessimistic]);

  if (loading || !data) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-80 w-full" />
          <Skeleton className="h-80 w-full" />
        </div>
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }

  // CO₂e saved percentage — use the backend-aggregated value from real receipt data.
  // The backend computes this from stored per-receipt co2e_central values where available,
  // falling back to energy savings for historical receipts.
  const co2eSavedPct = pessimistic
    ? Math.round(data.co2eSavedPct * 0.85)   // pessimistic: scale back by ~15%
    : data.co2eSavedPct;

  return (
    <div className="space-y-8">
      {/* Top 5 Stat Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatTile
          label="TOTAL REQUESTS"
          value={data.totalRequests.toLocaleString()}
          sublabel="this session"
        />
        <StatTile
          label="LLM CALLS AVOIDED"
          value={formatPct(data.llmCallsAvoidedPct)}
          sublabel={`${data.llmCallsAvoidedCount} requests`}
          color="accent"
        />
        <StatTile
          label="ENERGY SAVED"
          value={formatPct(data.energySavedPct)}
          sublabel="estimated"
          color="green"
        />
        <StatTile
          label="CO₂E SAVED"
          value={formatPct(co2eSavedPct)}
          sublabel="estimated"
          color="green"
        />
        <StatTile
          label="QUALITY RETENTION"
          value={formatPct(data.qualityRetentionPct, 1)}
          sublabel="vs baseline"
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Request Path Distribution */}
        <Card className="space-y-4 flex flex-col justify-between">
          <div>
            <SectionLabel className="mb-1">REQUEST PATH DISTRIBUTION</SectionLabel>
            <p className="text-xs text-muted font-sans">
              Proportion of workload resolved across architectural execution tiers.
            </p>
          </div>

          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.pathwayDistribution} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid stroke="#1E1E24" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="pathway"
                  tick={{ fill: '#5A5A64', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  tickFormatter={(val) => {
                    if (val === 'deterministic') return 'Tier 0';
                    if (val === 'cache') return 'Tier 0.5';
                    if (val === 'retrieval') return 'Tier 1';
                    if (val === 'small_model') return 'Tier 2';
                    if (val === 'large_model') return 'Tier 3';
                    if (val === 'escalated') return 'Escalated';
                    return val;
                  }}
                  axisLine={{ stroke: '#1E1E24' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#5A5A64', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                  axisLine={{ stroke: '#1E1E24' }}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const item = payload[0].payload;
                      return (
                        <div className="bg-surface2 border border-border rounded-lg p-2.5 shadow-xl font-mono text-xs space-y-1">
                          <div className="font-semibold text-text">{item.label}</div>
                          <div className="text-muted">
                            Requests: <span className="text-accent font-semibold">{item.count}</span>
                          </div>
                          <div className="text-dim text-[10px]">
                            Share: {((item.count / data.totalRequests) * 100).toFixed(1)}%
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {data.pathwayDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 pt-2 border-t border-border/60 text-xs font-mono">
            {data.pathwayDistribution.map((p) => (
              <div key={p.pathway} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: p.color }} />
                <span className="text-muted text-[11px]">{p.label.split(' ')[0]} ({p.count})</span>
              </div>
            ))}
          </div>
        </Card>

        {/* 2. Energy By Computational Pathway */}
        <Card className="space-y-4 flex flex-col justify-between">
          <div>
            <SectionLabel className="mb-1">ENERGY BY COMPUTATIONAL PATHWAY (WH)</SectionLabel>
            <p className="text-xs text-muted font-sans">
              Average single-request energy consumption by selected pathway.
            </p>
          </div>

          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={data.energyByPathwayWh}
                margin={{ top: 10, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid stroke="#1E1E24" strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  domain={[0, 0.8]}
                  tick={{ fill: '#5A5A64', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                  tickFormatter={(val) => `${val} Wh`}
                  axisLine={{ stroke: '#1E1E24' }}
                  tickLine={false}
                />
                <YAxis
                  dataKey="label"
                  type="category"
                  tick={{ fill: '#8A8A94', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                  axisLine={{ stroke: '#1E1E24' }}
                  tickLine={false}
                  width={90}
                />
                <Tooltip
                  cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const item = payload[0].payload;
                      return (
                        <div className="bg-surface2 border border-border rounded-lg p-2.5 shadow-xl font-mono text-xs space-y-1">
                          <div className="font-semibold text-text">{item.label}</div>
                          <div className="text-accent font-semibold">
                            {formatWh(item.energyWh)}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="energyWh" radius={[0, 4, 4, 0]}>
                  {data.energyByPathwayWh.map((entry, index) => (
                    <Cell key={`energy-cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="text-center text-[11px] font-mono text-dim pt-2 border-t border-border/60">
            Note: Tier 0 and Cache energy values are non-zero but orders of magnitude smaller.
          </div>
        </Card>
      </div>

      {/* 3. Cumulative Energy Divergence */}
      <Card className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <SectionLabel className="mb-1">CUMULATIVE ENERGY (WH)</SectionLabel>
            <p className="text-xs text-muted font-sans">
              Telemetry divergence over sequential requests: Always-large baseline vs AIFlow middleware.
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono shrink-0">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-t-2 border-dashed border-muted inline-block" />
              <span className="text-muted">Always-large baseline</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-accent inline-block" />
              <span className="text-accent font-semibold">AIFlow</span>
            </div>
          </div>
        </div>

        <div className="h-72 w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.cumulativeEnergy} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
              <CartesianGrid stroke="#1E1E24" strokeDasharray="3 3" />
              <XAxis
                dataKey="requestIndex"
                tick={{ fill: '#5A5A64', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                tickFormatter={(val) => `#${val}`}
                axisLine={{ stroke: '#1E1E24' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#5A5A64', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                tickFormatter={(val) => `${val} Wh`}
                axisLine={{ stroke: '#1E1E24' }}
                tickLine={false}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const baseVal = payload.find(p => p.dataKey === 'baselineWh')?.value as number;
                    const aiVal = payload.find(p => p.dataKey === 'aiflowWh')?.value as number;
                    const diff = Math.max(0, baseVal - aiVal);
                    const pct = baseVal > 0 ? ((diff / baseVal) * 100).toFixed(1) : '0';

                    return (
                      <div className="bg-surface2 border border-border rounded-lg p-3 shadow-xl font-mono text-xs space-y-1.5">
                        <div className="text-text font-bold">Request #{label}</div>
                        <div className="text-muted">
                          Baseline: <span className="text-text">{baseVal?.toFixed(1)} Wh</span>
                        </div>
                        <div className="text-accent font-semibold">
                          AIFlow: {aiVal?.toFixed(1)} Wh
                        </div>
                        <div className="text-ok text-[11px] pt-1 border-t border-border/50 font-bold">
                          Net Savings: {diff.toFixed(1)} Wh ({pct}%)
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Line
                type="monotone"
                dataKey="baselineWh"
                stroke="#8A8A94"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
                name="Baseline"
              />
              <Line
                type="monotone"
                dataKey="aiflowWh"
                stroke="#FF2D78"
                strokeWidth={2.5}
                dot={{ fill: '#FF2D78', r: 3 }}
                activeDot={{ r: 6, fill: '#FF2D78', stroke: '#FFFFFF', strokeWidth: 2 }}
                name="AIFlow"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
};
