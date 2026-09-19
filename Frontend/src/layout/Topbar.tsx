import React from 'react';
import { useLocation } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { MOCK_REGIONS } from '../mock/regions';
import { Select } from '../components/ui/Select';
import { AlertTriangle } from 'lucide-react';

export const Topbar: React.FC = () => {
  const location = useLocation();
  const { region, setRegion, qualityFloor, setQualityFloor, pessimistic } = useApp();

  // Dynamic route titles and subtitles
  let title = 'AIFlow Live Run';
  let subtitle = 'Watch AIFlow choose the minimum computational pathway for every request.';

  if (location.pathname.startsWith('/receipts')) {
    title = 'Energy Receipts';
    subtitle = 'An auditable record of how each request was processed.';
  } else if (location.pathname.startsWith('/audit')) {
    title = 'Audit Our Numbers';
    subtitle = 'AIFlow makes its own efficiency claims inspectable.';
  } else if (location.pathname.startsWith('/analytics')) {
    title = 'AIFlow Analytics';
    subtitle = 'Understand where your AI workload is spending compute.';
  }

  const regionOptions = MOCK_REGIONS.map((r) => ({
    value: r.id,
    label: r.label
  }));

  const qualityOptions = [
    { value: '0.45', label: 'Quality: 0.45 (Eco)' },
    { value: '0.60', label: 'Quality: 0.60 (Balanced)' },
    { value: '0.80', label: 'Quality: 0.80 (Frontier)' }
  ];

  return (
    <header className="h-[88px] sticky top-0 z-20 bg-bg/90 backdrop-blur-md border-b border-border px-4 lg:px-8 flex items-center justify-between">
      {/* Left: Page Title & Subtitle */}
      <div className="min-w-0 pr-4">
        <h1 className="text-xl md:text-2xl font-semibold text-text tracking-tight truncate">
          {title}
        </h1>
        <p className="text-xs md:text-sm text-muted truncate hidden sm:block">
          {subtitle}
        </p>
      </div>

      {/* Right: Controls & Profile */}
      <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
        {/* Pessimistic Mode Indicator Chip */}
        {pessimistic && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-warn/15 border border-warn/40 text-warn font-mono text-[11px] font-bold uppercase tracking-wider animate-pulse-subtle shadow-[0_0_12px_rgba(245,158,11,0.2)]">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="hidden md:inline">PESSIMISTIC</span>
          </div>
        )}

        {/* Region Selector */}
        <Select
          value={region.id}
          onChange={(newId) => {
            const found = MOCK_REGIONS.find((r) => r.id === newId);
            if (found) setRegion(found);
          }}
          options={regionOptions}
          aria-label="Execution Region Selector"
        />

        {/* Quality Floor Selector */}
        <Select
          value={qualityFloor.toFixed(2)}
          onChange={(newVal) => setQualityFloor(parseFloat(newVal))}
          options={qualityOptions}
          aria-label="Quality Floor Threshold"
        />

        {/* API Online Status Pill */}
        <div
          className="hidden xl:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-border bg-surface2/60 text-xs font-mono text-muted"
          title="Telemetry and routing microservices connected"
        >
          <span className="w-2 h-2 rounded-full bg-ok shadow-[0_0_6px_#22C55E]" />
          <span>API Online</span>
        </div>

        {/* User Initials Avatar */}
        <div
          className="w-9 h-9 rounded-full bg-gradient-to-br from-accent to-[#C026D3] text-white font-mono font-semibold text-xs flex items-center justify-center ring-1 ring-border shadow-[0_0_12px_rgba(255,45,120,0.25)] select-none shrink-0"
          title="David K. (DK)"
        >
          DK
        </div>
      </div>
    </header>
  );
};
