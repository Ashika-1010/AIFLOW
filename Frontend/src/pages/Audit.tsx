import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { AlertTriangle, RefreshCw, Play, FlaskConical } from 'lucide-react';

// ── Helper: format a metric that has no data yet ──────────────────────────────
function NoData({ label }: { label: string }) {
  return (
    <span className="font-mono text-dim text-sm" aria-label={`${label}: no data`}>
      —
    </span>
  );
}

export const Audit: React.FC = () => {
  const navigate = useNavigate();
  const { pessimistic, togglePessimistic } = useApp();
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getAuditSummary(pessimistic)
      .then(setSummary)
      .finally(() => setLoading(false));
  }, [pessimistic]);

  // Determine whether we have real data to show
  const hasRealData = (summary?.realExecutionCount ?? 0) > 0;
  const hasDemoOnly = !hasRealData && (summary?.demoCount ?? 0) > 0;

  // Animate the savings figure only when real data is present
  const targetSaving = pessimistic
    ? (summary?.pessimisticSavingPct ?? 0)
    : (summary?.centralSavingPct ?? 0);
  const animatedSaving = useCountUp(hasRealData ? targetSaving : 0, 600, 1);

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

  // ── Empty state (no real executions yet) ───────────────────────────────────
  if (!loading && !hasRealData) {
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

        {/* No runs yet */}
        <Card className="flex flex-col items-center justify-center py-16 space-y-5 text-center">
          <div className="w-14 h-14 rounded-full bg-surface2 flex items-center justify-center">
            <Play className="w-7 h-7 text-accent" />
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-text tracking-tight font-mono">
              No runs yet
            </h3>
            <p className="text-sm text-muted font-sans max-w-sm">
              Run your first prompt to generate an Energy Receipt.
              Audit metrics are calculated only from actual executions through AIFlow.
            </p>
          </div>
          <Button
            onClick={() => navigate('/')}
            leftIcon={<Play className="w-4 h-4" />}
          >
            Go to Live Run
          </Button>

          {/* Demo data notice when seed fixtures are present */}
          {hasDemoOnly && (
            <div className="mt-4 flex items-start gap-2.5 text-xs font-mono text-amber-400 bg-amber-400/10 border border-amber-400/30 rounded-lg p-3.5 max-w-md">
              <FlaskConical className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                <span className="font-bold">DEMO DATA PRESENT</span> — {summary!.demoCount} seeded fixture
                receipt{summary!.demoCount !== 1 ? 's' : ''} exist in the database for demonstration
                purposes but are excluded from all metric calculations above.
                They appear in the Receipts ledger labelled <span className="font-bold">DEMO</span>.
              </span>
            </div>
          )}
        </Card>

        {/* Assumptions table still useful even with no runs */}
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
  }

  // ── Main audit view (has real data, or still loading) ─────────────────────
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

      {/* Demo data notice — shown as a non-intrusive strip if demo records exist */}
      {!loading && hasDemoOnly === false && (summary?.demoCount ?? 0) > 0 && (
        <div className="flex items-start gap-2.5 text-xs font-mono text-amber-400/80 bg-amber-400/8 border border-amber-400/20 rounded-lg px-4 py-2.5">
          <FlaskConical className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>
            <span className="font-semibold">DEMO DATA EXCLUDED</span> — {summary!.demoCount} seeded
            fixture receipt{summary!.demoCount !== 1 ? 's' : ''} in the database are excluded from all
            metrics below. Metrics reflect only your {summary!.realExecutionCount} actual execution
            {summary!.realExecutionCount !== 1 ? 's' : ''}.
          </span>
        </div>
      )}

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
            disabled={!hasRealData}
            title={!hasRealData ? 'Run a prompt first to enable sensitivity analysis' : undefined}
          >
            {pessimistic
              ? 'Revert to Central Estimate ⇄'
              : 'Recalculate with Pessimistic Assumptions ⇄'}
          </Button>
        </div>

        {/* Warning strip when pessimistic is active */}
        {pessimistic && hasRealData && (
          <div className="p-3.5 rounded-lg bg-warn/15 border border-warn/40 text-warn flex items-start gap-2.5 text-xs font-mono animate-slide-up">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">⚠ Pessimistic assumptions applied:</span> PUE 1.25,
              high-end energy coefficients, upper-bound carbon intensity. Savings estimate revised
              from {formatPct(summary?.centralSavingPct ?? 0, 1)} →{' '}
              {formatPct(summary?.pessimisticSavingPct ?? 0, 1)}. Quality floor unchanged.
            </div>
          </div>
        )}

        {/* Two large tiles */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <StatTile
            label={pessimistic ? 'PESSIMISTIC ESTIMATE' : 'CENTRAL ESTIMATE'}
            value={loading ? '…' : hasRealData ? formatPct(animatedSaving, 1) : '—'}
            sublabel={
              hasRealData
                ? 'Estimated energy saving vs always-large baseline'
                : 'Run your first prompt to see this metric'
            }
            size="large"
            color={loading ? 'default' : hasRealData ? (pessimistic ? 'amber' : 'green') : 'default'}
          />
          <StatTile
            label="QUALITY RETENTION"
            value={
              loading
                ? '…'
                : hasRealData
                ? `${summary!.qualityRetentionPct.toFixed(1)}%`
                : '—'
            }
            sublabel={hasRealData ? 'Unchanged across sensitivity models' : 'No data yet'}
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
            AIFlow's routing overhead is charged against its own efficiency claims. These numbers are
            subtracted before savings are reported.
          </p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatTile
            label="ROUTER OVERHEAD"
            value={
              loading ? '…' : hasRealData
                ? formatPct(summary!.routerOverheadPct, 2)
                : <NoData label="Router overhead" />
            }
            sublabel="Subtracted from savings"
            color="accent"
          />
          <StatTile
            label="ESCALATION REGRET"
            value={
              loading ? '…' : hasRealData
                ? formatPct(summary!.escalationRegretPct, 2)
                : <NoData label="Escalation regret" />
            }
            sublabel="Failed cheap attempts"
            color="amber"
          />
          <StatTile
            label="FAILED CHEAP ATTEMPTS"
            value={
              loading ? '…' : hasRealData
                ? summary!.failedCheapAttempts.toString()
                : <NoData label="Failed cheap attempts" />
            }
            sublabel="Required escalation"
            color="red"
          />
          <StatTile
            label="HIDDEN SAVINGS"
            value={hasRealData ? '0' : <NoData label="Hidden savings" />}
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
