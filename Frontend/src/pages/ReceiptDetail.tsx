import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { getReceipt } from '../mock/api';
import type { Receipt } from '../mock/types';
import { Card } from '../components/ui/Card';
import { SectionLabel } from '../components/ui/SectionLabel';
import { StatTile } from '../components/ui/StatTile';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { RangeBar } from '../components/ui/RangeBar';
import { PathwayTrace } from '../components/PathwayTrace';
import { BaselineComparison } from '../components/BaselineComparison';
import { Skeleton } from '../components/ui/Skeleton';
import { formatLatency, formatUsd, formatCO2eRange, formatGridIntensity } from '../lib/format';
import { ArrowLeft, FlaskConical } from 'lucide-react';

export const ReceiptDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { region, pessimistic } = useApp();

  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    if (id) {
      getReceipt(id)
        .then((res) => {
          if (isMounted) setReceipt(res);
        })
        .catch((err) => {
          if (isMounted) setError(err.message || 'Failed to load receipt');
        })
        .finally(() => {
          if (isMounted) setLoading(false);
        });
    }

    return () => {
      isMounted = false;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-40 w-full" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-96 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  if (error || !receipt) {
    return (
      <div className="space-y-4 text-center py-16">
        <div className="text-xl font-mono text-danger">Receipt #{id} Not Found</div>
        <p className="text-sm text-muted">The requested receipt record could not be located in the ledger.</p>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/receipts')}
          leftIcon={<ArrowLeft className="w-4 h-4" />}
        >
          Back to Energy Receipts
        </Button>
      </div>
    );
  }

  // CO₂e estimate — prefer backend-computed values when available.
  // For historical/demo receipts without co2eGrams, fall back to the
  // frontend formula using the currently-selected region.
  // The pessimistic toggle is applied only to the frontend fallback path;
  // backend-provided values already use the region at request time.
  const hasCo2e = !!receipt?.co2eGrams;
  const fallbackMultiplier = pessimistic ? 1.4 : 1.0;
  const lowCO2e = hasCo2e
    ? receipt!.co2eGrams!.low
    : (receipt ? (receipt.energyWh.low / 1000) * region.gridIntensity * fallbackMultiplier : 0);
  const highCO2e = hasCo2e
    ? receipt!.co2eGrams!.high
    : (receipt ? (receipt.energyWh.high / 1000) * region.gridIntensity * fallbackMultiplier : 0);

  const co2eGridIntensity = hasCo2e
    ? receipt!.co2eGrams!.gridIntensityGPerKwh
    : region.gridIntensity;
  const co2eGridSource = hasCo2e
    ? receipt!.co2eGrams!.gridIntensitySource
    : 'static';

  const currentAiflowEnergy = pessimistic ? receipt.energyWh.high : receipt.energyWh.central;
  const currentBaselineEnergy = pessimistic ? receipt.baselineEnergyWh * 1.4 : receipt.baselineEnergyWh;

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <button
          onClick={() => navigate('/receipts')}
          className="inline-flex items-center gap-2 text-xs font-mono text-muted hover:text-text transition-colors py-1 cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to all receipts</span>
        </button>
      </div>

      {/* Demo receipt notice */}
      {receipt.isDemo && (
        <div className="flex items-start gap-2.5 text-xs font-mono text-amber-400 bg-amber-400/10 border border-amber-400/30 rounded-lg px-4 py-3">
          <FlaskConical className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            <span className="font-bold">DEMO RECEIPT</span> — This record is a pre-seeded fixture
            used to demonstrate the AIFlow interface. It is excluded from all Audit and Analytics
            metric calculations.
          </span>
        </div>
      )}

      {/* Header Banner */}
      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <SectionLabel>ENERGY RECEIPT</SectionLabel>
            {receipt.verification === 'passed' && (
              <Badge variant="verified" size="sm" />
            )}
            {receipt.verification === 'failed' && (
              <Badge variant="escalated" size="sm" />
            )}
            {receipt.verification === 'not_applicable' && (
              <Badge variant={receipt.pathway} size="sm" />
            )}
          </div>

          <div className="text-right">
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted mr-2">
              RECEIPT ID
            </span>
            <span className="font-mono text-lg font-bold text-accent">
              #{receipt.id}
            </span>
          </div>
        </div>

        <div className="text-xl md:text-2xl font-sans font-medium text-text">
          "{receipt.query}"
        </div>
      </Card>

      {/* Two Columns Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Pathway Trace & Decision Logic */}
          <Card>
            <PathwayTrace receipt={receipt} />
          </Card>

          {/* Computation Metrics (2x2 Grid) */}
          <Card className="space-y-4">
            <SectionLabel>COMPUTATION METRICS</SectionLabel>
            <div className="grid grid-cols-2 gap-4">
              <StatTile
                label="INPUT TOKENS"
                value={receipt.inputTokens.toString()}
                size="compact"
              />
              <StatTile
                label="OUTPUT TOKENS"
                value={receipt.outputTokens.toString()}
                size="compact"
              />
              <StatTile
                label="LATENCY"
                value={formatLatency(receipt.latencyMs)}
                size="compact"
              />
              <StatTile
                label="PROVIDER COST"
                value={formatUsd(receipt.providerCostUsd)}
                size="compact"
              />
            </div>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Estimated Energy (RangeBar) */}
          <Card className="space-y-4">
            <SectionLabel>ESTIMATED ENERGY</SectionLabel>
            <RangeBar energy={receipt.energyWh} />
            <div className="text-[11px] font-mono text-dim pt-2 border-t border-border/60">
              Estimate based on published energy coefficients and disclosed assumptions.
            </div>
          </Card>

          {/* CO2e Estimate Card */}
          <Card className="space-y-3">
            <SectionLabel>CO₂E ESTIMATE (estimated, not measured)</SectionLabel>

            <div className="text-2xl md:text-3xl font-mono font-bold text-text tabular-nums tracking-tight">
              {formatCO2eRange(lowCO2e, highCO2e)}
            </div>

            <div className="grid grid-cols-2 gap-4 py-2 border-y border-border/60 text-xs font-mono">
              <div>
                <span className="text-muted block text-[10px] uppercase tracking-wider">GRID INTENSITY</span>
                <span className="text-text font-semibold">{formatGridIntensity(co2eGridIntensity)}</span>
              </div>
              <div>
                <span className="text-muted block text-[10px] uppercase tracking-wider">
                  {hasCo2e ? 'REGION AT REQUEST TIME' : 'REGION (CURRENT)'}
                </span>
                <span className="text-accent font-semibold">
                  {hasCo2e ? receipt!.co2eGrams!.gridIntensitySource.toUpperCase() : region.label}
                </span>
              </div>
            </div>

            <div className="text-[11px] font-mono text-dim space-y-0.5">
              {hasCo2e ? (
                <span>
                  CO₂e computed by the backend at request time using the{' '}
                  {co2eGridSource === 'live' ? 'live' : 'static'} grid intensity for this region.
                  Carbon estimate changes with grid intensity; energy consumption does not.
                </span>
              ) : (
                <span>
                  CO₂e estimated client-side (historical receipt — no backend value available).
                  Calculation uses the currently selected region grid intensity and may differ
                  from the region active when this request was made.
                </span>
              )}
            </div>
          </Card>

          {/* Baseline Comparison */}
          <Card>
            <BaselineComparison
              aiflowEnergyWh={currentAiflowEnergy}
              baselineEnergyWh={currentBaselineEnergy}
            />
          </Card>
        </div>
      </div>
    </div>
  );
};
