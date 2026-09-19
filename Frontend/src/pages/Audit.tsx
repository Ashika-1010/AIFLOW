import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { Card } from '../components/ui/Card';
import { SectionLabel } from '../components/ui/SectionLabel';
import { StatTile } from '../components/ui/StatTile';
import { Button } from '../components/ui/Button';
import { Table, type Column } from '../components/ui/Table';
import { MOCK_ASSUMPTIONS } from '../mock/data';
import { getAuditSummary } from '../mock/api';
import type { AssumptionRow, AuditSummary } from '../mock/types';
import { useCountUp } from '../lib/useCountUp';
import { formatPct } from '../lib/format';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export const Audit: React.FC = () => {
  const { pessimistic, togglePessimistic } = useApp();
  const [summary, setSummary] = useState<AuditSummary | null>(null);

  useEffect(() => {
    getAuditSummary(pessimistic).then(setSummary);
  }, [pessimistic]);

  // Animate savings percentage between 42% and 31%
  const targetSaving = pessimistic ? 31.0 : 42.0;
  const animatedSaving = useCountUp(targetSaving, 600, 1);

  const assumptionColumns: Column<AssumptionRow>[] = [
    {
      key: 'parameter',
      header: 'PARAMETER',
      render: (row) => (
        <span className="font-mono text-text font-semibold text-xs">
          {row.parameter}
        </span>
      ),
      className: 'w-48'
    },
    {
      key: 'value',
      header: 'VALUE / SOURCE',
      render: (row) => (
        <div>
          <span className="font-mono text-accent font-medium text-xs block">
            {row.value}
          </span>
          <span className="text-dim text-[11px] font-mono block mt-0.5">
            {row.source}
          </span>
        </div>
      ),
      className: 'w-72'
    },
    {
      key: 'note',
      header: 'NOTE',
      render: (row) => (
        <span className="text-muted text-xs font-sans">
          {row.note}
        </span>
      )
    }
  ];

  return (
    <div className="space-y-8">
      {/* Transparency Banner */}
      <div className="border-l-4 border-accent bg-accentBg border-y border-r border-border rounded-xl p-6 space-y-2 shadow-[0_0_20px_rgba(255,45,120,0.06)]">
        <h2 className="text-xl md:text-2xl font-semibold text-text tracking-tight">
          "Our numbers are estimates. Here's exactly how we calculated them."
        </h2>
        <p className="text-sm text-muted font-sans">
          Every claim AIFlow makes is traceable to a specific assumption. Nothing is hidden.
        </p>
      </div>

      {/* PESSIMISTIC ESTIMATE — THE CENTREPIECE */}
      <Card
        variant={pessimistic ? 'amber' : 'default'}
        className="space-y-6 transition-all duration-300"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
          <div>
            <div className="flex items-center gap-2">
              <SectionLabel variant={pessimistic ? 'muted' : 'accent'}>
                {pessimistic ? (
                  <span className="text-warn font-bold flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    PESSIMISTIC ESTIMATE ACTIVE
                  </span>
                ) : (
                  'ESTIMATE SENSITIVITY'
                )}
              </SectionLabel>
            </div>
            <p className="text-sm text-muted font-sans mt-1">
              AIFlow does not hide uncertainty. Recalculate using less favorable assumptions.
            </p>
          </div>

          <Button
            variant={pessimistic ? 'amber' : 'ghost'}
            size="md"
            onClick={togglePessimistic}
            leftIcon={<RefreshCw className={`w-4 h-4 ${pessimistic ? 'animate-spin-slow' : ''}`} />}
            className="shrink-0 font-mono text-xs cursor-pointer"
          >
            {pessimistic
              ? 'Revert to Central Estimate ⇄'
              : 'Recalculate with Pessimistic Assumptions ⇄'}
          </Button>
        </div>

        {/* Warning strip when active */}
        {pessimistic && (
          <div className="p-3.5 rounded-lg bg-warn/15 border border-warn/40 text-warn flex items-start gap-2.5 text-xs font-mono animate-slide-up">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">⚠ Pessimistic assumptions applied:</span> PUE 1.25, high-end energy coefficients, upper-bound carbon intensity. Savings estimate revised from 42% → 31%. Quality floor unchanged.
            </div>
          </div>
        )}

        {/* Two large tiles */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <StatTile
            label={pessimistic ? 'PESSIMISTIC ESTIMATE' : 'CENTRAL ESTIMATE'}
            value={formatPct(animatedSaving, 1)}
            sublabel="Estimated energy saving vs always-large baseline"
            size="large"
            color={pessimistic ? 'amber' : 'green'}
          />
          <StatTile
            label="QUALITY RETENTION"
            value="98.7%"
            sublabel="Unchanged across sensitivity models"
            size="large"
            color="default"
          />
        </div>
      </Card>

      {/* SELF-ACCOUNTING */}
      <div className="space-y-3">
        <div>
          <SectionLabel className="mb-1">SELF-ACCOUNTING & PENALTIES</SectionLabel>
          <p className="text-sm text-muted font-sans">
            AIFlow's routing overhead is charged against its own efficiency claims. These numbers are subtracted before savings are reported.
          </p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatTile
            label="ROUTER OVERHEAD"
            value="1.2%"
            sublabel="Subtracted from savings"
            color="accent"
          />
          <StatTile
            label="ESCALATION REGRET"
            value="2.4%"
            sublabel="Failed cheap attempts"
            color="amber"
          />
          <StatTile
            label="FAILED CHEAP ATTEMPTS"
            value={summary ? summary.failedCheapAttempts.toString() : '3'}
            sublabel="Required escalation"
            color="red"
          />
          <StatTile
            label="HIDDEN SAVINGS"
            value="0"
            sublabel="Nothing excluded"
            color="green"
          />
        </div>
      </div>

      {/* ASSUMPTIONS TABLE */}
      <div className="space-y-3">
        <div>
          <SectionLabel className="mb-1">DISCLOSED BENCHMARK ASSUMPTIONS</SectionLabel>
          <p className="text-xs text-muted font-sans">
            All parameters derived from published peer-reviewed datasets and verified industry benchmarks.
          </p>
        </div>

        <Table<AssumptionRow>
          columns={assumptionColumns}
          data={MOCK_ASSUMPTIONS}
          keyExtractor={(row) => row.parameter}
        />
      </div>
    </div>
  );
};
