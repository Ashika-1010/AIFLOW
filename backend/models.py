"""
Pydantic schemas — field names match src/mock/types.ts exactly.
Do not rename any field; the frontend deserialises by exact key name.
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


PathwayLiteral = Literal[
    "deterministic", "cache", "retrieval",
    "small_model", "large_model", "escalated"
]

VerificationLiteral = Literal["passed", "failed", "not_applicable"]


class EnergyBand(BaseModel):
    low: float
    central: float
    high: float


class Co2eGrams(BaseModel):
    """
    Per-receipt CO₂e estimate in grams (gCO₂e), three uncertainty bands.

    Formula: co2e_g = (energy_wh / 1000) × grid_intensity_g_per_kwh

    Values are estimates, not measured emissions.
    Present only on receipts generated after the CO₂e tracking feature was
    added.  Absent (null) on historical/demo receipts.
    """
    low: float
    central: float
    high: float
    gridIntensityGPerKwh: int    # grid intensity used — gCO₂e/kWh
    gridIntensitySource: str     # "static" or "live"


class Receipt(BaseModel):
    id: str
    timestamp: str
    query: str
    pathway: PathwayLiteral
    pathwaySteps: list[str]
    reason: str
    complexityScore: float
    qualityFloor: float
    predictedSufficiency: float
    verification: VerificationLiteral
    escalated: bool
    inputTokens: int
    outputTokens: int
    latencyMs: int
    providerCostUsd: float
    energyWh: EnergyBand
    baselineEnergyWh: float
    routerOverheadWh: float
    escalationRegretWh: float
    response: str
    # Optional flag — True for seed/demo rows, False for real executions.
    # The frontend uses this to label demo rows in the Receipts ledger.
    isDemo: bool = False
    # CO₂e estimate in gCO₂e, three uncertainty bands.
    # None for historical receipts that pre-date CO₂e tracking.
    co2eGrams: Optional[Co2eGrams] = None


class CompleteRequest(BaseModel):
    query: str
    qualityFloor: float = Field(default=0.60, ge=0.0, le=1.0)
    region: str = Field(default="IN")
    # Filename of a document previously uploaded to the corpus via POST /v1/documents.
    # When provided, the pipeline skips similarity gating and directly grounds its
    # response in that document's content.
    docFilename: Optional[str] = None


class AuditSummary(BaseModel):
    routerOverheadPct: float
    escalationRegretPct: float
    failedCheapAttempts: int
    hiddenSavings: int  # always 0 per spec
    centralSavingPct: float
    pessimisticSavingPct: float
    qualityRetentionPct: float
    # Metadata fields — not part of the original mock contract but added
    # transparently so the frontend can distinguish real vs demo data.
    realExecutionCount: int = 0   # number of actual (non-demo) receipts
    demoCount: int = 0            # number of demo/seed receipts in DB


class PathwayDistributionItem(BaseModel):
    pathway: PathwayLiteral
    label: str
    count: int
    color: str


class EnergyByPathwayItem(BaseModel):
    pathway: PathwayLiteral
    label: str
    energyWh: float
    color: str


class CumulativeEnergyPoint(BaseModel):
    requestIndex: int
    baselineWh: float
    aiflowWh: float


class AnalyticsPayload(BaseModel):
    totalRequests: int
    llmCallsAvoidedCount: int
    llmCallsAvoidedPct: float
    energySavedPct: float
    co2eSavedPct: float
    qualityRetentionPct: float
    pathwayDistribution: list[PathwayDistributionItem]
    energyByPathwayWh: list[EnergyByPathwayItem]
    cumulativeEnergy: list[CumulativeEnergyPoint]


class HealthResponse(BaseModel):
    status: str = "ok"
