import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { listReceipts } from '../mock/api';
import { Table, type Column } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Skeleton } from '../components/ui/Skeleton';
import { formatWh, formatLatency } from '../lib/format';
import type { Receipt } from '../mock/types';
import { ArrowRight, Play } from 'lucide-react';
import { SectionLabel } from '../components/ui/SectionLabel';

export const Receipts: React.FC = () => {
  const navigate = useNavigate();
  const { receipts: contextReceipts } = useApp();
  const [apiReceipts, setApiReceipts] = useState<Receipt[] | null>(null);

  useEffect(() => {
    listReceipts()
      .then(setApiReceipts)
      .catch(() => setApiReceipts([]));
  }, []);

  // Merge: API receipts are the baseline; new session runs (in context) prepend
  const receipts: Receipt[] = React.useMemo(() => {
    if (apiReceipts === null) return [];
    const apiIds = new Set(apiReceipts.map(r => r.id));
    const newOnes = contextReceipts.filter(r => !apiIds.has(r.id));
    return [...newOnes, ...apiReceipts];
  }, [apiReceipts, contextReceipts]);

  const loading = apiReceipts === null;

  const columns: Column<Receipt>[] = [
    {
      key: 'id',
      header: 'RECEIPT ID',
      render: (r) => (
        <div className="flex items-center gap-2">
          <span className="font-mono text-accent font-semibold tracking-wider">
            #{r.id}
          </span>
          {r.isDemo && (
            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border border-amber-400/40 text-amber-400/80 bg-amber-400/10 leading-none">
              DEMO
            </span>
          )}
        </div>
      ),
      className: 'w-36'
    },
    {
      key: 'query',
      header: 'QUERY',
      render: (r) => (
        <div className="max-w-md truncate font-sans text-text text-sm" title={r.query}>
          {r.query}
        </div>
      )
    },
    {
      key: 'pathway',
      header: 'PATHWAY',
      render: (r) => <Badge variant={r.pathway} size="sm" />,
      className: 'w-36'
    },
    {
      key: 'energyWh',
      header: 'EST. ENERGY',
      render: (r) => (
        <span className="font-mono text-text font-medium">
          {formatWh(r.energyWh.central)}
        </span>
      ),
      className: 'w-32 font-mono'
    },
    {
      key: 'latency',
      header: 'LATENCY',
      render: (r) => (
        <span className="font-mono text-muted">
          {formatLatency(r.latencyMs)}
        </span>
      ),
      className: 'w-24 font-mono'
    },
    {
      key: 'verification',
      header: 'VERIFIED',
      render: (r) => {
        if (r.verification === 'passed') {
          return <span className="font-mono text-ok font-bold">✓</span>;
        }
        if (r.verification === 'failed') {
          return <span className="font-mono text-danger font-bold">✗</span>;
        }
        return <span className="font-mono text-dim font-bold">—</span>;
      },
      className: 'w-24 text-center',
      headerClassName: 'text-center'
    },
    {
      key: 'action',
      header: '',
      render: () => (
        <span className="text-muted group-hover:text-accent flex items-center justify-end">
          <ArrowRight className="w-4 h-4 opacity-70" />
        </span>
      ),
      className: 'w-10 text-right'
    }
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionLabel>AUDITABLE TELEMETRY LEDGER ({receipts.length} RECORDS)</SectionLabel>
        <div className="text-xs font-mono text-dim">Click any row to inspect full receipt</div>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      ) : (
        <Table<Receipt>
          columns={columns}
          data={receipts}
          keyExtractor={(r) => r.id}
          onRowClick={(r) => navigate(`/receipts/${r.id}`)}
          emptyMessage={
            <div className="py-12 text-center space-y-3">
              <p className="text-muted text-sm font-mono">No requests yet.</p>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/')}
                leftIcon={<Play className="w-3.5 h-3.5" />}
              >
                Go to Live Run
              </Button>
            </div>
          }
        />
      )}
    </div>
  );
};
