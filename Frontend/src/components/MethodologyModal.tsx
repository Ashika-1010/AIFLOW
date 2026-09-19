import React from 'react';
import { Modal } from './ui/Modal';
import { SectionLabel } from './ui/SectionLabel';
import { METHODOLOGY_DATA } from '../mock/methodology';
import { MOCK_ASSUMPTIONS } from '../mock/data';
import { useApp } from '../context/AppContext';

export const MethodologyModal: React.FC = () => {
  const { methodologyModalOpen, setMethodologyModalOpen } = useApp();

  return (
    <Modal
      isOpen={methodologyModalOpen}
      onClose={() => setMethodologyModalOpen(false)}
      title="AIFlow Methodology & Accounting Framework"
      subtitle={`Specification Version: ${METHODOLOGY_DATA.version} · Disclosed Parameters`}
      maxWidth="2xl"
    >
      {/* 1. Core Formulas */}
      <div>
        <SectionLabel className="mb-2">ESTIMATION FORMULAS</SectionLabel>
        <div className="space-y-2.5 font-mono text-xs">
          {METHODOLOGY_DATA.formulas.map((f, i) => (
            <div key={i} className="p-3 bg-surface2/70 border border-border rounded-lg">
              <div className="text-text font-semibold mb-1 text-accent">{f.name}</div>
              <div className="bg-bg/80 p-2 rounded border border-border/60 text-emerald-400 select-all mb-1.5 overflow-x-auto">
                <code>{f.equation}</code>
              </div>
              <div className="text-muted text-[11px] font-sans">{f.description}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 2. Tier Energy Profiles */}
      <div>
        <SectionLabel className="mb-2">TIER COMPUTATION PROFILES</SectionLabel>
        <div className="space-y-2 font-mono text-xs">
          {Object.entries(METHODOLOGY_DATA.tiers).map(([key, tier]) => (
            <div key={key} className="p-3 bg-surface2/50 border border-border rounded-lg">
              <div className="text-text font-medium text-xs mb-1">{tier.description}</div>
              {tier.whPer1kOutput && (
                <div className="text-muted text-[11px] space-y-0.5">
                  <div>
                    Output Energy: <span className="text-text">{tier.whPer1kOutput.low} (low) / {tier.whPer1kOutput.central} (central) / {tier.whPer1kOutput.high} (high) Wh/1k tokens</span>
                  </div>
                  <div>
                    Prompt Energy: <span className="text-text">{tier.whPer1kPrompt?.low} / {tier.whPer1kPrompt?.central} / {tier.whPer1kPrompt?.high} Wh/1k tokens</span>
                  </div>
                </div>
              )}
              {tier.whPerQuery && (
                <div className="text-muted text-[11px]">
                  Query Energy: <span className="text-text">{tier.whPerQuery.low} / {tier.whPerQuery.central} / {tier.whPerQuery.high} Wh/query</span>
                </div>
              )}
              <div className="text-dim text-[10px] mt-1 font-sans">Source: {tier.source}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 3. Disclosed Assumptions Table */}
      <div>
        <SectionLabel className="mb-2">DISCLOSED ASSUMPTIONS</SectionLabel>
        <div className="border border-border rounded-lg overflow-hidden font-mono text-xs">
          <table className="w-full text-left">
            <thead className="bg-surface2 text-muted border-b border-border text-[10px] uppercase tracking-wider">
              <tr>
                <th className="py-2 px-3">Parameter</th>
                <th className="py-2 px-3">Value / Source</th>
                <th className="py-2 px-3">Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {MOCK_ASSUMPTIONS.map((row, i) => (
                <tr key={i} className="hover:bg-surface2/30">
                  <td className="py-2 px-3 text-text font-medium">{row.parameter}</td>
                  <td className="py-2 px-3 text-accent">{row.value}</td>
                  <td className="py-2 px-3 text-muted text-[11px] font-sans">{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Explicit Exclusions */}
      <div>
        <SectionLabel className="mb-2">EXPLICIT BOUNDARY EXCLUSIONS</SectionLabel>
        <ul className="list-disc list-inside space-y-1 text-xs text-muted font-sans">
          {METHODOLOGY_DATA.exclusions.map((exc, i) => (
            <li key={i}>{exc}</li>
          ))}
        </ul>
      </div>

      {/* 5. Published Citations */}
      <div>
        <SectionLabel className="mb-2">PUBLISHED CITATIONS</SectionLabel>
        <div className="space-y-1.5 text-[11px] text-dim font-mono">
          {METHODOLOGY_DATA.citations.map((cite, i) => (
            <div key={i} className="p-2 bg-surface2/30 border border-border/40 rounded">
              {cite}
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
};
