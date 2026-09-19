import React from 'react';
import type { Receipt } from '../mock/types';
import { getPathwayConfig } from '../lib/colors';
import { SectionLabel } from './ui/SectionLabel';
import { CheckCircle2, XCircle, ArrowRight, BrainCircuit, ShieldCheck, Sparkles } from 'lucide-react';
import { formatPct } from '../lib/format';

interface PathwayTraceProps {
  receipt: Receipt;
}

export const PathwayTrace: React.FC<PathwayTraceProps> = ({ receipt }) => {
  const config = getPathwayConfig(receipt.pathway);

  // Check if a step corresponds to the active chosen pathway
  const isHighlightedStep = (step: string) => {
    const s = step.toLowerCase();
    if (receipt.pathway === 'deterministic' && (s.includes('deterministic') || s.includes('eval') || s.includes('gate'))) return true;
    if (receipt.pathway === 'cache' && s.includes('cache')) return true;
    if (receipt.pathway === 'retrieval' && (s.includes('retrieval') || s.includes('rag') || s.includes('corpus'))) return true;
    if (receipt.pathway === 'small_model' && s.includes('small')) return true;
    if (receipt.pathway === 'large_model' && s.includes('large')) return true;
    if (receipt.pathway === 'escalated' && (s.includes('escalat') || s.includes('large'))) return true;
    return false;
  };

  return (
    <div className="space-y-6">
      {/* COMPUTATIONAL PATHWAY CHIPS */}
      <div>
        <SectionLabel className="mb-3">COMPUTATIONAL PATHWAY</SectionLabel>
        <div className="flex flex-wrap items-center gap-2">
          {receipt.pathwaySteps.map((step, index) => {
            const isHighlight = isHighlightedStep(step);
            return (
              <React.Fragment key={index}>
                <div
                  className={`px-3 py-1.5 rounded-lg border text-xs font-mono transition-all duration-200 ${
                    isHighlight
                      ? `${config.pillBg} font-semibold shadow-[0_0_16px_rgba(255,45,120,0.25)] ring-1 ring-accent/30`
                      : 'bg-surface2/60 border-border text-muted'
                  }`}
                >
                  {step}
                </div>
                {index < receipt.pathwaySteps.length - 1 && (
                  <ArrowRight className="w-3.5 h-3.5 text-dim shrink-0" />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* WHY THIS PATH? */}
      <div>
        <SectionLabel className="mb-3">WHY THIS PATH?</SectionLabel>
        
        {/* 3 Metric Tiles */}
        <div className="grid grid-cols-3 gap-3 mb-5">
          <div className="bg-surface2/50 border border-border rounded-lg p-3">
            <div className="text-[10px] font-mono text-muted uppercase tracking-wider mb-1">
              COMPLEXITY SCORE
            </div>
            <div className="text-lg font-mono font-semibold text-text tabular-nums">
              {receipt.complexityScore.toFixed(2)}
            </div>
          </div>
          <div className="bg-surface2/50 border border-border rounded-lg p-3">
            <div className="text-[10px] font-mono text-muted uppercase tracking-wider mb-1">
              QUALITY FLOOR
            </div>
            <div className="text-lg font-mono font-semibold text-accent tabular-nums">
              {receipt.qualityFloor.toFixed(2)}
            </div>
          </div>
          <div className="bg-surface2/50 border border-border rounded-lg p-3">
            <div className="text-[10px] font-mono text-muted uppercase tracking-wider mb-1">
              PREDICTED SUFFICIENCY
            </div>
            <div className="text-lg font-mono font-semibold text-text tabular-nums">
              {formatPct(receipt.predictedSufficiency * 100)}
            </div>
          </div>
        </div>

        {/* Vertical 3-Step Trace */}
        <div className="relative pl-6 space-y-4 border-l-2 border-border/80 ml-3 py-1">
          {/* 1. PREDICT */}
          <div className="relative">
            <div className="absolute -left-[31px] top-0.5 w-6 h-6 rounded-md bg-surface2 border border-border flex items-center justify-center text-accent">
              <BrainCircuit className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="flex items-center gap-2 font-mono text-xs font-semibold uppercase text-text tracking-wide">
                <span>PREDICT</span>
                <span className="text-muted font-normal text-[11px]">
                  {formatPct(receipt.predictedSufficiency * 100)} predicted sufficient
                </span>
              </div>
              <p className="text-xs text-dim font-sans mt-0.5">
                Input features and complexity evaluated against required quality floor.
              </p>
            </div>
          </div>

          {/* 2. VERIFY */}
          <div className="relative">
            <div className="absolute -left-[31px] top-0.5 w-6 h-6 rounded-md bg-surface2 border border-border flex items-center justify-center">
              {receipt.verification === 'passed' ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-ok" />
              ) : receipt.verification === 'failed' ? (
                <XCircle className="w-3.5 h-3.5 text-danger" />
              ) : (
                <ShieldCheck className="w-3.5 h-3.5 text-muted" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2 font-mono text-xs font-semibold uppercase text-text tracking-wide">
                <span>VERIFY</span>
                <span className="text-[11px] font-normal">
                  {receipt.verification === 'passed' && <span className="text-ok font-mono">✓ Passed quality gate</span>}
                  {receipt.verification === 'failed' && <span className="text-danger font-mono">✗ Failed quality gate</span>}
                  {receipt.verification === 'not_applicable' && <span className="text-muted font-mono">— Direct gate match</span>}
                </span>
              </div>
              <p className="text-xs text-dim font-sans mt-0.5">
                {receipt.verification === 'failed'
                  ? 'Candidate output failed confidence/structural gate; escalated to frontier tier.'
                  : receipt.verification === 'passed'
                  ? 'Output verified for structural correctness and confidence threshold.'
                  : 'Deterministic or cached response bypassed verification step.'}
              </p>
            </div>
          </div>

          {/* 3. DECIDE */}
          <div className="relative">
            <div className="absolute -left-[31px] top-0.5 w-6 h-6 rounded-md bg-surface2 border border-border flex items-center justify-center text-ok">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="flex items-center gap-2 font-mono text-xs font-semibold uppercase text-text tracking-wide">
                <span>DECIDE</span>
                <span className="text-[11px] font-mono text-text">
                  {receipt.pathway === 'deterministic' && 'Return deterministic calculation'}
                  {receipt.pathway === 'cache' && 'Return cached payload directly'}
                  {receipt.pathway === 'retrieval' && 'Return grounded corpus response'}
                  {receipt.pathway === 'small_model' && 'Return small-model response'}
                  {receipt.pathway === 'large_model' && 'Return large-model response'}
                  {receipt.pathway === 'escalated' && 'Escalate and return large-model response'}
                </span>
              </div>
              <p className="text-xs text-muted font-mono mt-1 italic">
                "{receipt.reason}"
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
