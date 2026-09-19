export interface MethodologyData {
  version: string;
  pue: { low: number; central: number; high: number };
  tiers: Record<string, {
    description: string;
    whPer1kOutput?: { low: number; central: number; high: number };
    whPer1kPrompt?: { low: number; central: number; high: number };
    whPerQuery?: { low: number; central: number; high: number };
    source: string;
  }>;
  formulas: {
    name: string;
    equation: string;
    description: string;
  }[];
  exclusions: string[];
  citations: string[];
}

export const METHODOLOGY_DATA: MethodologyData = {
  version: "aiflow-em-1.0",
  pue: {
    low: 1.09,
    central: 1.15,
    high: 1.25
  },
  tiers: {
    tier3_large: {
      description: "Tier 3: Large LLM (70B+/405B Frontier / Reasoning)",
      whPer1kOutput: { low: 0.28, central: 0.58, high: 1.10 },
      whPer1kPrompt: { low: 0.03, central: 0.07, high: 0.14 },
      source: "ML.ENERGY v3.0 405B-class; Google Gemini inference methodology comprehensive boundary (2025)"
    },
    tier2_small: {
      description: "Tier 2: Small LLM (8B-class)",
      whPer1kOutput: { low: 0.012, central: 0.024, high: 0.048 },
      whPer1kPrompt: { low: 0.002, central: 0.004, high: 0.008 },
      source: "ML.ENERGY v3.0 8B-class; ~15-25x lower energy per token than 70B+"
    },
    tier1_retrieval: {
      description: "Tier 1: Retrieval / Local Corpus RAG",
      whPerQuery: { low: 0.0001, central: 0.0003, high: 0.0006 },
      source: "MiniLM embedding + in-memory vector cosine similarity over ~200 docs"
    },
    tier0_5_cache: {
      description: "Tier 0.5: Exact & Semantic Cache",
      whPerQuery: { low: 0.00001, central: 0.00002, high: 0.00004 },
      source: "In-memory SHA-256 hash / dense cosine embedding lookup"
    },
    tier0_deterministic: {
      description: "Tier 0: Deterministic Tools (AST / regex / sympy / dateutil)",
      whPerQuery: { low: 0.0000005, central: 0.000001, high: 0.000003 },
      source: "CPU-only execution — reported as negligible (~0.000 Wh), not zero"
    }
  },
  formulas: [
    {
      name: "Compute Energy (E_compute)",
      equation: "E_compute (Wh) = Σ_tier [ (prompt_tokens × e_prefill_tier) + (output_tokens × e_decode_tier) ]",
      description: "Aggregates prefill and decode energy across tiers based on measured per-token coefficients."
    },
    {
      name: "Total Energy (E_total)",
      equation: "E_total = E_compute × PUE",
      description: "Multiplies raw compute energy by the Datacenter Power Usage Effectiveness (PUE: 1.09 - 1.25, central 1.15)."
    },
    {
      name: "Carbon Emissions (CO₂e)",
      equation: "CO₂e (g) = (E_total / 1000) × CI",
      description: "Converts total watt-hours to kilowatt-hours and scales by the regional grid carbon intensity (CI in gCO₂e/kWh)."
    },
    {
      name: "Net Energy Savings",
      equation: "Savings = E_baseline - (E_aiflow + Router_overhead + Escalation_regret)",
      description: "Charges AIFlow for its own classification compute and any wasted energy incurred during cheap-first verification failures."
    }
  ],
  exclusions: [
    "Embodied carbon from server manufacturing, silicon fabrication, and transport is excluded.",
    "Data center water consumption (direct evaporative cooling & indirect thermoelectric water) is excluded.",
    "Hardware-level GPU telemetry is not measured directly; energy is modeled from published benchmark coefficients for FP8 H100-class serving."
  ],
  citations: [
    "ML.ENERGY Benchmark v3.0 (2025) — Per-token and per-query energy benchmarks for open frontier models.",
    "Google Gemini inference methodology (Aug 2025) — 'Measuring the environmental impact of AI inference' (PUE 1.09, comprehensive vs accelerator boundaries).",
    "'The Price of Prompting' (arXiv 2407.16893) & TokenPowerBench — Super-linear energy growth across model parameter classes.",
    "Electricity Maps — Published regional grid emission factors (annual average and real-time carbon intensity)."
  ]
};
