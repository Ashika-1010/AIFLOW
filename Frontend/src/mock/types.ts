export type Pathway = 'deterministic' | 'cache' | 'retrieval' | 'small_model' | 'large_model' | 'escalated';

export interface EnergyBand {
  low: number;
  central: number;
  high: number;
} // Wh

export interface Receipt {
  id: string;                    // "AF-0284"
  timestamp: string;             // ISO
  query: string;
  pathway: Pathway;
  pathwaySteps: string[];        // ["Request","Analysis","Small Model","Verification","Response"]
  reason: string;                // "Arithmetic expression detected"
  complexityScore: number;       // 0..1
  qualityFloor: number;          // 0..1
  predictedSufficiency: number;  // 0..1
  verification: 'passed' | 'failed' | 'not_applicable';
  escalated: boolean;
  inputTokens: number;
  outputTokens: number;
  latencyMs: number;
  providerCostUsd: number;
  energyWh: EnergyBand;
  baselineEnergyWh: number;      // always-large counterfactual
  routerOverheadWh: number;
  escalationRegretWh: number;    // 0 unless escalated
  response: string;
}

export interface AuditSummary {
  routerOverheadPct: number;
  escalationRegretPct: number;
  failedCheapAttempts: number;
  hiddenSavings: 0;              // always 0 — "nothing excluded"
  centralSavingPct: number;
  pessimisticSavingPct: number;
  qualityRetentionPct: number;
}

export interface Region {
  id: string;
  label: string;
  gridIntensity: number;         // gCO2e/kWh
}

export interface AssumptionRow {
  parameter: string;
  value: string;
  source: string;
  note: string;
}

export interface AnalyticsPayload {
  totalRequests: number;
  llmCallsAvoidedCount: number;
  llmCallsAvoidedPct: number;
  energySavedPct: number;
  co2eSavedPct: number;
  qualityRetentionPct: number;
  pathwayDistribution: {
    pathway: Pathway;
    label: string;
    count: number;
    color: string;
  }[];
  energyByPathwayWh: {
    pathway: Pathway;
    label: string;
    energyWh: number;
    color: string;
  }[];
  cumulativeEnergy: {
    requestIndex: number;
    baselineWh: number;
    aiflowWh: number;
  }[];
}
