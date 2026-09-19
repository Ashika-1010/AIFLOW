import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Play, FileText, Clock, LineChart } from 'lucide-react';
import { useApp } from '../context/AppContext';

interface NavItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { name: 'Live Run', path: '/', icon: Play },
  { name: 'Energy Receipts', path: '/receipts', icon: FileText },
  { name: 'Audit', path: '/audit', icon: Clock },
  { name: 'Analytics', path: '/analytics', icon: LineChart },
];

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { setMethodologyModalOpen } = useApp();

  const isRouteActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <aside className="fixed top-0 left-0 h-screen w-[72px] lg:w-[280px] bg-[#0B0B0D] border-r border-border flex flex-col justify-between z-30 select-none transition-all duration-200">
      {/* Top Logo & Nav */}
      <div>
        {/* Brand Logo Header */}
        <div className="h-[88px] px-4 lg:px-6 flex items-center gap-3.5 border-b border-border">
          <div className="w-10 h-10 shrink-0 rounded-lg bg-gradient-to-br from-accent to-[#C026D3] flex items-center justify-center shadow-[0_0_24px_rgba(255,45,120,0.35)] ring-1 ring-white/20">
            {/* Diamond glyph */}
            <svg
              className="w-5 h-5 text-white"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M12 2L2 12l10 10 10-12L12 2z" />
            </svg>
          </div>
          <div className="hidden lg:flex items-center text-xl font-semibold tracking-tight">
            <span className="text-white">AI</span>
            <span className="text-accent font-bold">Flow</span>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="p-3 lg:p-4 space-y-1.5" aria-label="Main Navigation">
          {NAV_ITEMS.map((item) => {
            const active = isRouteActive(item.path);
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`relative flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-all duration-150 ${
                  active
                    ? 'bg-accentBg text-accent'
                    : 'text-muted hover:text-text hover:bg-surface2/60'
                }`}
              >
                {/* 3px flush left active bar */}
                {active && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-[3px] bg-accent rounded-r"
                    aria-hidden="true"
                  />
                )}

                <Icon className={`w-5 h-5 shrink-0 ${active ? 'text-accent' : 'text-muted'}`} />
                <span className="hidden lg:inline-block font-sans">{item.name}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom Pinned Footer */}
      <div className="p-4 lg:p-6 border-t border-border space-y-2">
        {/* Operational Status Dot */}
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2.5 w-2.5 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ok opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-ok shadow-[0_0_8px_#22C55E]" />
          </span>
          <span className="hidden lg:inline text-xs font-sans text-muted">
            All systems operational
          </span>
        </div>

        {/* Methodology Link Button */}
        <div>
          <button
            type="button"
            onClick={() => setMethodologyModalOpen(true)}
            className="text-left font-mono text-xs text-dim hover:text-accent transition-colors cursor-pointer py-1"
            title="Open Methodology & Accounting Documentation"
          >
            <span className="hidden lg:inline">Methodology v1.0</span>
            <span className="lg:hidden text-[10px]">v1.0</span>
          </button>
        </div>
      </div>
    </aside>
  );
};
