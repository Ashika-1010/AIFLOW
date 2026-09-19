import type { Receipt, AuditSummary, AnalyticsPayload, Pathway } from './types';
import { MOCK_RECEIPTS } from './data';

// Demo error simulation flag (as per spec §4)
export const SIMULATE_ERRORS = false;

// In-memory store for receipts during session
let dynamicReceipts: Receipt[] = [...MOCK_RECEIPTS];
let nextReceiptNumber = 285;

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Executes a simulated request through the AIFlow middleware.
 * NOTE: For demo realism, pathways are selected via deterministic string matching
 * and threshold heuristics rather than full ML runtime inference.
 */
export async function runRequest(query: string, qualityFloor: number = 0.60): Promise<Receipt> {
  const simulatedDelay = Math.floor(Math.random() * 400) + 400; // 400 - 800ms
  await delay(simulatedDelay);

  if (SIMULATE_ERRORS && Math.random() < 0.20) {
    throw new Error('Simulation Error: Provider connection timed out. Please retry.');
  }

  const normalized = query.trim().toLowerCase();
  const id = `AF-0${nextReceiptNumber++}`;
  const timestamp = new Date().toISOString();

  // 1. Arithmetic / deterministic patterns
  const isArithmetic = /^(\s*what\s+is\s+)?[\d\s+\-*/×÷()^.]+(\s*\?)?$/i.test(normalized) ||
    /(\d+)\s*([*×x/+\-])\s*(\d+)/i.test(normalized) ||
    normalized.includes('convert') ||
    normalized.includes('how many days between') ||
    normalized.includes('calculate');

  // 2. Large model / deep analysis patterns
  const isLarge = normalized.includes('analyze') ||
    normalized.includes('technical document') ||
    normalized.includes('consensus') ||
    normalized.includes('modal realism') ||
    normalized.includes('post-mortem') ||
    normalized.includes('distributed systems');

  // 3. Borderline prompt: "Explain quantum entanglement simply"
  const isQuantumBorderline = normalized.includes('quantum entanglement') && !normalized.includes('wave function');

  // 4. Exact/Semantic cache checks
  const existingFixture = dynamicReceipts.find(
    r => r.query.toLowerCase().trim() === normalized && r.pathway === 'cache'
  );

  let pathway: Pathway;
  let steps: string[];
  let reason: string;
  let complexityScore: number;
  let predictedSufficiency: number;
  let verification: 'passed' | 'failed' | 'not_applicable' = 'passed';
  let escalated = false;
  let inputTokens = Math.max(12, Math.floor(query.length / 3));
  let outputTokens = 60;
  let latencyMs = 380;
  let providerCostUsd = 0.0006;
  let energyWh = { low: 0.012, central: 0.018, high: 0.031 };
  let baselineEnergyWh = 0.081;
  let routerOverheadWh = 0.0000010;
  let escalationRegretWh = 0;
  let response = '';

  if (isArithmetic) {
    pathway = 'deterministic';
    steps = ['Request', 'Analysis', 'Deterministic Gate', 'AST Safe Eval', 'Response'];
    reason = normalized.includes('convert') ? 'Unit conversion detected' :
      normalized.includes('days') ? 'Date arithmetic detected' : 'Arithmetic expression detected';
    complexityScore = 0.02;
    predictedSufficiency = 1.00;
    verification = 'not_applicable';
    latencyMs = Math.floor(Math.random() * 4) + 2; // 2-5ms
    providerCostUsd = 0.0000;
    energyWh = { low: 0.0000005, central: 0.000001, high: 0.000003 };
    baselineEnergyWh = 0.075;
    routerOverheadWh = 0.0000004;

    // Evaluate simple math if possible
    if (normalized.includes('27') && (normalized.includes('43') || normalized.includes('×') || normalized.includes('*'))) {
      response = 'What is 27 × 43 = 1161';
    } else if (normalized.includes('1024')) {
      response = '1024 * 1024 = 1048576';
    } else if (normalized.includes('120') && normalized.includes('miles')) {
      response = '120 mph = 193.121 km/h';
    } else {
      response = `Computed deterministically via AST safe evaluation: Result = ${(42 + Math.floor(Math.random() * 100))}`;
    }
  } else if (existingFixture) {
    pathway = 'cache';
    steps = ['Request', 'Analysis', 'Semantic Cache', 'Response'];
    reason = 'Semantic cache hit, cosine 0.96';
    complexityScore = 0.04;
    predictedSufficiency = 0.99;
    verification = 'not_applicable';
    latencyMs = Math.floor(Math.random() * 10) + 4;
    providerCostUsd = 0.0000;
    energyWh = { low: 0.000010, central: 0.000020, high: 0.000040 };
    baselineEnergyWh = 0.070;
    routerOverheadWh = 0.0000006;
    response = existingFixture.response;
  } else if (isQuantumBorderline) {
    // Demonstrates Quality floor knob behavior
    if (qualityFloor >= 0.75) {
      pathway = 'large_model';
      steps = ['Request', 'Analysis', 'Quality Threshold Gate', 'Large Model (70B+)', 'Response'];
      reason = `Routed to large model: Quality floor ${qualityFloor.toFixed(2)} exceeds small-model sufficiency (0.65); high depth selected`;
      complexityScore = 0.65;
      predictedSufficiency = 0.65;
      verification = 'not_applicable';
      latencyMs = 2150;
      providerCostUsd = 0.0125;
      inputTokens = 120;
      outputTokens = 350;
      energyWh = { low: 0.310, central: 0.580, high: 1.100 };
      baselineEnergyWh = 0.580;
      response = 'Quantum entanglement is a phenomenon in quantum mechanics where two or more particles become interconnected such that the state of one cannot be described independently of the state of the other, even when separated by vast distances. Measurement collapses the shared entangled state instantaneously.';
    } else {
      pathway = 'small_model';
      steps = ['Request', 'Analysis', 'Small Model (8B)', 'Verification', 'Response'];
      reason = `Routed to small model: p_small=0.68 ≥ floor ${qualityFloor.toFixed(2)}; general explanation sufficient`;
      complexityScore = 0.35;
      predictedSufficiency = 0.68;
      verification = 'passed';
      latencyMs = 460;
      providerCostUsd = 0.0008;
      inputTokens = 24;
      outputTokens = 90;
      energyWh = { low: 0.012, central: 0.018, high: 0.031 };
      baselineEnergyWh = 0.095;
      response = 'Quantum entanglement is when two particles become deeply linked so that measuring something about one (like its spin) instantly reveals the corresponding state of the other, no matter the distance between them.';
    }
  } else if (isLarge) {
    pathway = 'large_model';
    steps = ['Request', 'Analysis', 'Complexity Router', 'Large Model (70B+)', 'Response'];
    reason = 'Routed to large model: technical document analysis requested; complexity score 0.89 > threshold';
    complexityScore = 0.89;
    predictedSufficiency = 0.32;
    verification = 'not_applicable';
    latencyMs = Math.floor(Math.random() * 800) + 2100;
    inputTokens = 1420;
    outputTokens = 520;
    providerCostUsd = 0.0182;
    energyWh = { low: 0.310, central: 0.580, high: 1.100 };
    baselineEnergyWh = 0.580;
    routerOverheadWh = 0.0000024;
    response = 'Summary of Consensus Trade-offs:\n1. Understandability: Raft decomposes consensus into leader election, log replication, and safety, making state transitions formal and auditable.\n2. Performance: Multi-Paxos allows pipelining under asymmetric network partitions with fewer round-trips when leadership is stable.\n3. Implementation Complexity: Multi-Paxos corner cases in log compaction and view changes introduce significant subtle failure states compared to Raft.';
  } else {
    // Default Small Model pathway
    pathway = 'small_model';
    steps = ['Request', 'Analysis', 'Small Model (8B)', 'Verification', 'Response'];
    reason = `Routed to small model: p_small=0.87 ≥ floor ${qualityFloor.toFixed(2)}; no document attached; ${inputTokens} prompt tokens`;
    complexityScore = 0.21;
    predictedSufficiency = 0.87;
    verification = 'passed';
    latencyMs = Math.floor(Math.random() * 150) + 360;
    inputTokens = 184;
    outputTokens = 96;
    providerCostUsd = 0.0008;
    energyWh = { low: 0.012, central: 0.018, high: 0.031 };
    baselineEnergyWh = 0.081;
    routerOverheadWh = 0.0000012;

    if (normalized.includes('rewrite') || normalized.includes('professionally')) {
      response = 'Here is the revised paragraph: "Please find attached the updated quarterly performance report. Should you require further clarification regarding the financial telemetry or projections, please feel free to reach out."';
    } else {
      response = `AIFlow processed your request via the 8B-class model pathway. The output meets all verification gates with confidence score exceeding the active quality floor (${qualityFloor.toFixed(2)}).`;
    }
  }

  const receipt: Receipt = {
    id,
    timestamp,
    query,
    pathway,
    pathwaySteps: steps,
    reason,
    complexityScore,
    qualityFloor,
    predictedSufficiency,
    verification,
    escalated,
    inputTokens,
    outputTokens,
    latencyMs,
    providerCostUsd,
    energyWh,
    baselineEnergyWh,
    routerOverheadWh,
    escalationRegretWh,
    response
  };

  // Prepend to dynamic list
  dynamicReceipts = [receipt, ...dynamicReceipts];

  return receipt;
}

export async function listReceipts(): Promise<Receipt[]> {
  await delay(350);
  return [...dynamicReceipts];
}

export async function getReceipt(id: string): Promise<Receipt> {
  await delay(300);
  const found = dynamicReceipts.find(r => r.id === id);
  if (!found) {
    throw new Error(`Receipt ${id} not found`);
  }
  return found;
}

export async function getAuditSummary(pessimistic: boolean = false): Promise<AuditSummary> {
  await delay(320);
  return {
    routerOverheadPct: 1.2,
    escalationRegretPct: 2.4,
    failedCheapAttempts: 3,
    hiddenSavings: 0,
    centralSavingPct: 42.0,
    pessimisticSavingPct: pessimistic ? 31.0 : 42.0,
    qualityRetentionPct: 98.7
  };
}

export async function getAnalytics(pessimistic: boolean = false): Promise<AnalyticsPayload> {
  await delay(400);

  const totalRequests = 1240;
  const llmCallsAvoidedCount = 384;
  const llmCallsAvoidedPct = 31;
  const energySavedPct = pessimistic ? 31 : 37;
  const co2eSavedPct = pessimistic ? 29 : 34;
  const qualityRetentionPct = 98.2;

  const pathwayDistribution: AnalyticsPayload['pathwayDistribution'] = [
    { pathway: 'deterministic', label: 'Deterministic (Tier 0)', count: 260, color: '#22C55E' },
    { pathway: 'cache', label: 'Cache (Tier 0.5)', count: 124, color: '#A855F7' },
    { pathway: 'retrieval', label: 'Retrieval (Tier 1)', count: 85, color: '#6366F1' },
    { pathway: 'small_model', label: 'Small Model (Tier 2)', count: 520, color: '#FF2D78' },
    { pathway: 'large_model', label: 'Large Model (Tier 3)', count: 218, color: '#F59E0B' },
    { pathway: 'escalated', label: 'Escalated', count: 33, color: '#EF4444' }
  ];

  const energyMultiplier = pessimistic ? 1.85 : 1.0;

  const energyByPathwayWh: AnalyticsPayload['energyByPathwayWh'] = [
    { pathway: 'deterministic', label: 'Deterministic', energyWh: +(0.000001 * energyMultiplier).toFixed(6), color: '#22C55E' },
    { pathway: 'cache', label: 'Cache Hit', energyWh: +(0.000020 * energyMultiplier).toFixed(5), color: '#A855F7' },
    { pathway: 'retrieval', label: 'Retrieval', energyWh: +(0.000300 * energyMultiplier).toFixed(4), color: '#6366F1' },
    { pathway: 'small_model', label: 'Small Model', energyWh: +(0.018 * energyMultiplier).toFixed(3), color: '#FF2D78' },
    { pathway: 'large_model', label: 'Large Model', energyWh: +(0.580 * energyMultiplier).toFixed(3), color: '#F59E0B' },
    { pathway: 'escalated', label: 'Escalated', energyWh: +(0.598 * energyMultiplier).toFixed(3), color: '#EF4444' }
  ];

  // 20 points showing divergence over requests
  const cumulativeEnergy: AnalyticsPayload['cumulativeEnergy'] = [];
  let cumBase = 0;
  let cumAiflow = 0;
  for (let i = 1; i <= 20; i++) {
    const reqIndex = i * 62;
    cumBase += 0.38 * (pessimistic ? 1.4 : 1.0) * (50 + Math.sin(i) * 8);
    cumAiflow += 0.15 * (pessimistic ? 1.3 : 1.0) * (45 + Math.cos(i) * 6);
    cumulativeEnergy.push({
      requestIndex: reqIndex,
      baselineWh: Math.round(cumBase * 10) / 10,
      aiflowWh: Math.round(cumAiflow * 10) / 10
    });
  }

  return {
    totalRequests,
    llmCallsAvoidedCount,
    llmCallsAvoidedPct,
    energySavedPct,
    co2eSavedPct,
    qualityRetentionPct,
    pathwayDistribution,
    energyByPathwayWh,
    cumulativeEnergy
  };
}
