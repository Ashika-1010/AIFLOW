import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { runRequest, uploadDocument } from '../mock/api';
import type { Receipt } from '../mock/types';
import { Card } from '../components/ui/Card';
import { SectionLabel } from '../components/ui/SectionLabel';
import { StatTile } from '../components/ui/StatTile';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { ExampleChips } from '../components/ExampleChips';
import { Skeleton } from '../components/ui/Skeleton';
import { formatWh, formatLatency } from '../lib/format';
import { ArrowRight, AlertCircle, RefreshCw, CheckCircle2 } from 'lucide-react';

export const LiveRun: React.FC = () => {
  const navigate = useNavigate();
  const { qualityFloor, region, sessionStats, recordSessionRequest, liveRunPrompt, setLiveRunPrompt } = useApp();

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [resultReceipt, setResultReceipt] = useState<Receipt | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null);
  const [pinnedDocFilename, setPinnedDocFilename] = useState<string | null>(null);
  
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleRun = async (queryToRun?: string) => {
    const text = (queryToRun || liveRunPrompt).trim();
    if (!text || isLoading) return;

    setIsLoading(true);
    setErrorMessage(null);

    // Snapshot and immediately clear the pinned doc so subsequent runs
    // don't re-use it unless the user uploads again.
    const docFilename = pinnedDocFilename ?? undefined;
    setPinnedDocFilename(null);
    setUploadSuccessMessage(null);

    try {
      const receipt = await runRequest(text, qualityFloor, region.id, docFilename);
      setResultReceipt(receipt);
      recordSessionRequest(receipt);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : 'An unexpected error occurred during execution.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectExample = (exampleText: string) => {
    setLiveRunPrompt(exampleText);
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleUploadDocument = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setErrorMessage(null);
    setUploadSuccessMessage(null);

    try {
      const result = await uploadDocument(file);
      // Store the filename so the next Run call pins this document.
      setPinnedDocFilename(result.filename);
      setUploadSuccessMessage(`"${result.filename}" uploaded — next run will use this document.`);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : 'An unexpected error occurred during upload.'
      );
    } finally {
      setIsUploading(false);
      if (e.target) {
        e.target.value = ''; // Reset input so the same file can be re-selected
      }
    }
  };

  const getLlmCallsCount = (r: Receipt): number => {
    if (r.pathway === 'deterministic' || r.pathway === 'cache') return 0;
    if (r.pathway === 'escalated') return 2;
    return 1;
  };

  const getVerificationDisplay = (r: Receipt) => {
    if (r.verification === 'passed') return '✓ Passed';
    if (r.verification === 'failed') return '✗ Failed';
    return 'N/A';
  };

  return (
    <div className="space-y-8">
      {/* CARD A: TRY A REQUEST */}
      <Card className="space-y-4">
        <div>
          <SectionLabel className="mb-1">TRY A REQUEST</SectionLabel>
          <p className="text-sm text-muted font-sans">
            Send a request through AIFlow and watch the decision engine work.
          </p>
        </div>

        {/* Textarea */}
        <div className="bg-surface2/40 border border-border/70 rounded-xl p-4 focus-within:border-accent/80 focus-within:ring-1 focus-within:ring-accent/80 transition-all">
          <textarea
            value={liveRunPrompt}
            onChange={(e) => setLiveRunPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleRun();
              }
            }}
            placeholder="Ask anything…"
            rows={4}
            className="w-full bg-transparent text-text font-sans placeholder-dim resize-none focus:outline-none text-base leading-relaxed"
          />
        </div>

        {/* Divider */}
        <div className="border-t border-border pt-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <ExampleChips onSelect={handleSelectExample} disabled={isLoading} />

          <div className="flex flex-col md:flex-row gap-3 w-full md:w-auto shrink-0">
            <input 
              type="file" 
              accept=".txt,.pdf,.doc,.docx" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              onChange={handleUploadDocument} 
            />
            <Button
              variant="ghost"
              onClick={handleUploadClick}
              disabled={isUploading || isLoading}
              isLoading={isUploading}
              size="lg"
              className="w-full md:w-auto shrink-0"
            >
              {isUploading ? 'Uploading…' : 'Upload Document'}
            </Button>
            <Button
              onClick={() => handleRun()}
              disabled={!liveRunPrompt.trim() || isLoading}
              isLoading={isLoading}
              size="lg"
              className="w-full md:w-auto shrink-0"
            >
              {isLoading ? 'Analyzing…' : pinnedDocFilename ? 'Run with Document' : 'Run with AIFlow'}
            </Button>
          </div>
        </div>
      </Card>

      {/* SUCCESS STATE */}
      {uploadSuccessMessage && (
        <div className="p-4 rounded-xl border border-green-500/40 bg-green-500/10 text-green-400 flex items-center justify-between gap-4 animate-fade-in">
          <div className="flex items-center gap-2.5 text-sm">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <span>{uploadSuccessMessage}</span>
          </div>
          <button
            onClick={() => { setUploadSuccessMessage(null); setPinnedDocFilename(null); }}
            className="text-green-400 hover:text-green-200 text-xs font-mono transition-colors shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ERROR STATE */}
      {errorMessage && (
        <div className="p-4 rounded-xl border border-danger/40 bg-danger/10 text-danger flex items-center justify-between gap-4 animate-fade-in">
          <div className="flex items-center gap-2.5 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleRun()}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Retry
          </Button>
        </div>
      )}

      {/* LOADING SKELETON */}
      {isLoading && (
        <Card className="space-y-6 animate-fade-in">
          <div className="flex justify-between items-center">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-6 w-40" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
          <Skeleton className="h-28 w-full" />
        </Card>
      )}

      {/* CARD B: RESULT CARD */}
      {!isLoading && resultReceipt && (
        <Card className="space-y-6 animate-slide-up border-border">
          {/* Header Row */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-border">
            <div className="flex items-center gap-3">
              <Badge variant={resultReceipt.pathway} size="lg" />
              <span className="text-sm font-medium text-text">Pathway selected</span>
            </div>

            <button
              onClick={() => navigate(`/receipts/${resultReceipt.id}`)}
              className="inline-flex items-center gap-1.5 text-xs font-mono text-accent hover:text-white px-3 py-1.5 rounded-lg border border-accent/40 bg-accentBg hover:bg-accent/20 transition-all cursor-pointer"
            >
              <span>View Energy Receipt</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Two columns: REQUEST & WHY THIS PATH */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <SectionLabel variant="muted" className="mb-1.5">
                REQUEST
              </SectionLabel>
              <p className="text-base text-text font-mono font-medium">
                {resultReceipt.query}
              </p>
            </div>
            <div>
              <SectionLabel variant="muted" className="mb-1.5">
                WHY THIS PATH?
              </SectionLabel>
              <p className="text-base text-text font-sans font-medium text-muted">
                "{resultReceipt.reason}"
              </p>
            </div>
          </div>

          {/* 4-Up Grid of StatTiles */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatTile
              label="LATENCY"
              value={formatLatency(resultReceipt.latencyMs)}
            />
            <StatTile
              label="EST. ENERGY"
              value={formatWh(resultReceipt.energyWh.central)}
              tooltip={
                resultReceipt.energyWh.central < 0.0005
                  ? 'Non-zero but below display precision (~0.000 Wh)'
                  : undefined
              }
            />
            <StatTile
              label="LLM CALLS"
              value={getLlmCallsCount(resultReceipt).toString()}
            />
            <StatTile
              label="VERIFICATION"
              value={getVerificationDisplay(resultReceipt)}
              color={
                resultReceipt.verification === 'passed'
                  ? 'green'
                  : resultReceipt.verification === 'failed'
                  ? 'red'
                  : 'default'
              }
            />
          </div>

          {/* Bordered Response Box */}
          <div className="border border-border bg-surface2/40 rounded-xl p-4 space-y-2">
            <SectionLabel variant="muted">
              RESPONSE — GENERATED VIA {resultReceipt.pathway.toUpperCase()} RESOLUTION
            </SectionLabel>
            <div className="text-sm font-mono text-text whitespace-pre-wrap leading-relaxed">
              {resultReceipt.response}
            </div>
          </div>
        </Card>
      )}

      {/* CARD C: SESSION STRIP */}
      <div className="pt-2">
        <SectionLabel className="mb-3">SESSION TELEMETRY</SectionLabel>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatTile
            label="REQUESTS THIS SESSION"
            value={sessionStats.requests.toString()}
            sublabel="Total interactive executions"
          />
          <StatTile
            label="LLM CALLS AVOIDED"
            value={sessionStats.llmCallsAvoided.toString()}
            sublabel="Resolved via deterministic / cache"
            color="accent"
          />
          <StatTile
            label="EST. ENERGY SAVED"
            value={formatWh(sessionStats.estEnergySavedWh)}
            sublabel="Net vs always-large counterfactual"
            color="green"
          />
        </div>
      </div>
    </div>
  );
};
