"""
AIFlow Backend — FastAPI application
Implements exactly the contract in Frontend/src/mock/api.ts
"""
from __future__ import annotations
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv()

from db import init_db, get_db, ReceiptORM, SessionLocal
from models import (
    Receipt, CompleteRequest, AuditSummary,
    AnalyticsPayload, HealthResponse,
    PathwayDistributionItem, EnergyByPathwayItem, CumulativeEnergyPoint,
)
from engine.classifier import load_metrics as load_classifier_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pathway display metadata — keep in sync with frontend colors
# ---------------------------------------------------------------------------
_PATHWAY_META = {
    "deterministic": {"label": "Deterministic (Tier 0)", "color": "#22C55E"},
    "cache":         {"label": "Cache (Tier 0.5)",        "color": "#A855F7"},
    "retrieval":     {"label": "Retrieval (Tier 1)",      "color": "#6366F1"},
    "small_model":   {"label": "Small Model (Tier 2)",    "color": "#FF2D78"},
    "large_model":   {"label": "Large Model (Tier 3)",    "color": "#F59E0B"},
    "escalated":     {"label": "Escalated",               "color": "#EF4444"},
}

_AVOIDED_PATHWAYS = {"deterministic", "cache", "retrieval"}

# ---------------------------------------------------------------------------
# Startup: load sentence-transformer, rebuild cache index, load retrieval corpus
# ---------------------------------------------------------------------------
_sentence_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _sentence_model

    # 1. Create DB tables
    init_db()
    logger.info("Database initialised")

    # 2. Load sentence transformer
    logger.info("Loading SentenceTransformer (all-MiniLM-L6-v2)…")
    from sentence_transformers import SentenceTransformer
    _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("SentenceTransformer loaded")

    # 3. Rebuild semantic cache index
    from engine.cache import rebuild_index_from_db
    db = SessionLocal()
    try:
        rebuild_index_from_db(db)
    finally:
        db.close()

    # 4. Load retrieval corpus
    from engine.retrieval import get_retrieval_engine
    get_retrieval_engine().load(
        lambda texts: _sentence_model.encode(texts, show_progress_bar=False).tolist()
    )

    logger.info("AIFlow backend ready")
    yield
    logger.info("AIFlow backend shutting down")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AIFlow API",
    version="1.0.0",
    description="AI routing middleware with real energy accounting",
    lifespan=lifespan,
)

# CORS — allow Vite dev origin and * in dev mode
_DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
_allowed_origins = ["http://localhost:5173", "http://localhost:4173"]
if _DEV_MODE:
    _allowed_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: ORM row → Pydantic Receipt
# ---------------------------------------------------------------------------
def _orm_to_receipt(row: ReceiptORM) -> Receipt:
    return Receipt(**row.to_pydantic())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/health", response_model=HealthResponse, tags=["health"])
def health():
    return HealthResponse(status="ok")


@app.post("/v1/complete", response_model=Receipt, tags=["core"])
def complete(req: CompleteRequest, db: Session = Depends(get_db)):
    """
    Execute a request through the AIFlow decision pipeline.
    Returns a Receipt with real energy accounting.
    """
    if _sentence_model is None:
        raise HTTPException(503, "Model not loaded yet — please retry")

    from engine.decision import run_pipeline
    try:
        receipt_dict = run_pipeline(
            query=req.query,
            quality_floor=req.qualityFloor,
            region=req.region,
            sentence_model=_sentence_model,
            db=db,
            doc_filename=req.docFilename,
        )
    except Exception as exc:
        logger.exception("Pipeline error: %s", exc)
        raise HTTPException(500, f"Pipeline error: {exc}") from exc

    # Persist to DB
    co2e = receipt_dict.get("co2eGrams")
    orm = ReceiptORM(
        id=receipt_dict["id"],
        timestamp=receipt_dict["timestamp"],
        query=receipt_dict["query"],
        pathway=receipt_dict["pathway"],
        pathway_steps=json.dumps(receipt_dict["pathwaySteps"]),
        reason=receipt_dict["reason"],
        complexity_score=receipt_dict["complexityScore"],
        quality_floor=receipt_dict["qualityFloor"],
        predicted_sufficiency=receipt_dict["predictedSufficiency"],
        verification=receipt_dict["verification"],
        escalated=receipt_dict["escalated"],
        input_tokens=receipt_dict["inputTokens"],
        output_tokens=receipt_dict["outputTokens"],
        latency_ms=receipt_dict["latencyMs"],
        provider_cost_usd=receipt_dict["providerCostUsd"],
        energy_wh=json.dumps(receipt_dict["energyWh"]),
        baseline_energy_wh=receipt_dict["baselineEnergyWh"],
        router_overhead_wh=receipt_dict["routerOverheadWh"],
        escalation_regret_wh=receipt_dict["escalationRegretWh"],
        response=receipt_dict["response"],
        region=req.region,
        co2e_low=co2e["low"] if co2e else None,
        co2e_central=co2e["central"] if co2e else None,
        co2e_high=co2e["high"] if co2e else None,
        co2e_grid_intensity=co2e["gridIntensityGPerKwh"] if co2e else None,
        co2e_grid_source=co2e["gridIntensitySource"] if co2e else None,
    )
    db.add(orm)
    db.commit()

    return Receipt(**receipt_dict)


@app.get("/v1/receipts", response_model=list[Receipt], tags=["receipts"])
def list_receipts(db: Session = Depends(get_db)):
    """Return all receipts, newest first."""
    rows = db.query(ReceiptORM).order_by(ReceiptORM.created_at.desc()).all()
    return [_orm_to_receipt(r) for r in rows]


@app.get("/v1/receipts/{receipt_id}", response_model=Receipt, tags=["receipts"])
def get_receipt(receipt_id: str, db: Session = Depends(get_db)):
    """Return a single receipt by ID."""
    row = db.query(ReceiptORM).filter(ReceiptORM.id == receipt_id).first()
    if row is None:
        raise HTTPException(404, f"Receipt {receipt_id} not found")
    return _orm_to_receipt(row)


@app.get("/v1/audit", response_model=AuditSummary, tags=["analytics"])
def get_audit(
    pessimistic: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """
    Return audit summary computed ONLY from real execution receipts (is_demo=False).
    Demo/seed receipts are counted but never included in metric calculations.
    Returns realExecutionCount=0 and null-safe metric values when no real runs exist.
    """
    # Split into real vs demo rows — only real rows drive metrics
    real_rows = db.query(ReceiptORM).filter(ReceiptORM.is_demo == False).all()  # noqa: E712
    demo_count = db.query(ReceiptORM).filter(ReceiptORM.is_demo == True).count()  # noqa: E712

    if not real_rows:
        # No real executions yet — return a clean empty state.
        # All metric fields are null-safe: 0 or None signals "no data" to the frontend.
        return AuditSummary(
            routerOverheadPct=0.0,
            escalationRegretPct=0.0,
            failedCheapAttempts=0,
            hiddenSavings=0,
            centralSavingPct=0.0,
            pessimisticSavingPct=0.0,
            qualityRetentionPct=0.0,
            realExecutionCount=0,
            demoCount=demo_count,
        )

    rows = real_rows
    total_baseline   = sum(r.baseline_energy_wh for r in rows)
    total_overhead   = sum(r.router_overhead_wh  for r in rows)
    total_regret     = sum(r.escalation_regret_wh for r in rows)
    failed_cheap     = sum(1 for r in rows if r.escalated)

    # Energy band to use
    band = "high" if pessimistic else "central"
    total_aiflow = sum(json.loads(r.energy_wh)[band] for r in rows)
    total_aiflow += total_overhead

    if total_baseline > 0:
        raw_saving = (total_baseline - total_aiflow) / total_baseline * 100
        central_saving = max(0.0, round(raw_saving, 1))
    else:
        central_saving = 0.0

    # Pessimistic: high PUE factor (1.25 / 1.15) applied on top of high energy band
    if pessimistic:
        pessimistic_saving = max(0.0, round(central_saving * (1.15 / 1.25), 1))
    else:
        pessimistic_saving = central_saving

    router_pct = (total_overhead / total_baseline * 100) if total_baseline > 0 else 0.0
    regret_pct = (total_regret  / total_baseline * 100) if total_baseline > 0 else 0.0

    quality_retention = (
        ((len(rows) - failed_cheap) / len(rows) * 100) if rows else 0.0
    )

    return AuditSummary(
        routerOverheadPct=round(router_pct, 2),
        escalationRegretPct=round(regret_pct, 2),
        failedCheapAttempts=failed_cheap,
        hiddenSavings=0,
        centralSavingPct=central_saving,
        pessimisticSavingPct=pessimistic_saving,
        qualityRetentionPct=round(quality_retention, 1),
        realExecutionCount=len(rows),
        demoCount=demo_count,
    )


@app.get("/v1/analytics", response_model=AnalyticsPayload, tags=["analytics"])
def get_analytics(
    pessimistic: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """Return analytics payload computed ONLY from real execution receipts (is_demo=False)."""
    rows = db.query(ReceiptORM).filter(
        ReceiptORM.is_demo == False  # noqa: E712
    ).order_by(ReceiptORM.created_at.asc()).all()

    if not rows:
        # Seed placeholder response
        return _empty_analytics()

    band = "high" if pessimistic else "central"

    # ── Pathway distribution ──────────────────────────────────────────────
    pathway_counts: dict[str, int] = {}
    for r in rows:
        pathway_counts[r.pathway] = pathway_counts.get(r.pathway, 0) + 1

    # Ensure all 6 pathways appear
    for pw in _PATHWAY_META:
        pathway_counts.setdefault(pw, 0)

    pathway_distribution = [
        PathwayDistributionItem(
            pathway=pw,
            label=_PATHWAY_META[pw]["label"],
            count=pathway_counts[pw],
            color=_PATHWAY_META[pw]["color"],
        )
        for pw in _PATHWAY_META
    ]

    # ── Energy by pathway (average per request) ──────────────────────────
    pathway_energy: dict[str, list[float]] = {pw: [] for pw in _PATHWAY_META}
    for r in rows:
        e = json.loads(r.energy_wh)[band]
        pathway_energy[r.pathway].append(e)

    energy_by_pathway = [
        EnergyByPathwayItem(
            pathway=pw,
            label=_PATHWAY_META[pw]["label"].split(" ")[0]
                  + (" Hit" if pw == "cache" else ""),
            energyWh=round(
                sum(pathway_energy[pw]) / max(1, len(pathway_energy[pw])),
                6,
            ),
            color=_PATHWAY_META[pw]["color"],
        )
        for pw in _PATHWAY_META
    ]

    # ── Top-level stats ───────────────────────────────────────────────────
    total = len(rows)
    avoided_count = sum(1 for r in rows if r.pathway in _AVOIDED_PATHWAYS)
    avoided_pct   = round(avoided_count / total * 100, 1) if total else 0.0

    total_baseline = sum(r.baseline_energy_wh for r in rows)
    total_aiflow   = sum(json.loads(r.energy_wh)[band] + r.router_overhead_wh for r in rows)

    energy_saved_pct = round(
        max(0, (total_baseline - total_aiflow) / total_baseline * 100), 1
    ) if total_baseline else 0.0

    # CO₂e savings percentage — derived from receipts that have backend-computed
    # co2e_central values (rows since the CO₂e tracking feature was added).
    # For rows with NULL co2e columns (historical receipts), we fall back to
    # the energy-proportional approximation so historical data isn't silently dropped.
    # The baseline CO₂e uses each receipt's own stored grid intensity so mixed-region
    # workloads are handled correctly.
    rows_with_co2e    = [r for r in rows if r.co2e_central is not None
                         and r.co2e_grid_intensity is not None]
    rows_without_co2e = [r for r in rows if r.co2e_central is None]

    if rows_with_co2e:
        from sustainability.calculator import compute_co2e
        # Baseline CO₂e: always-large-model at central band × same grid intensity
        total_co2e_baseline = sum(
            compute_co2e(r.baseline_energy_wh, r.co2e_grid_intensity)
            for r in rows_with_co2e
        )
        total_co2e_aiflow = sum(r.co2e_central for r in rows_with_co2e)
        # Add energy-proportional estimate for legacy rows
        if rows_without_co2e and total_baseline > 0:
            legacy_baseline = sum(r.baseline_energy_wh for r in rows_without_co2e)
            legacy_aiflow   = sum(json.loads(r.energy_wh)[band] for r in rows_without_co2e)
            legacy_ratio    = (total_co2e_baseline / sum(r.baseline_energy_wh for r in rows_with_co2e)
                               if rows_with_co2e else 1.0)
            total_co2e_baseline += legacy_baseline * legacy_ratio
            total_co2e_aiflow   += legacy_aiflow   * legacy_ratio

        co2e_saved_pct = round(
            max(0, (total_co2e_baseline - total_co2e_aiflow) / total_co2e_baseline * 100), 1
        ) if total_co2e_baseline else 0.0
    else:
        # No receipts with CO₂e data yet — use energy savings as an approximation
        # and label it explicitly in logs so it is traceable.
        logger.debug(
            "No receipts with co2e_central data; using energy_saved_pct as co2e_saved_pct proxy"
        )
        co2e_saved_pct = energy_saved_pct

    # Quality retention
    escalated_count = sum(1 for r in rows if r.escalated)
    quality_retention = round((total - escalated_count) / total * 100, 1) if total else 100.0

    # ── Cumulative energy divergence ─────────────────────────────────────
    cumulative: list[CumulativeEnergyPoint] = []
    cum_base   = 0.0
    cum_aiflow = 0.0
    step = max(1, total // 20)  # ~20 data points
    for i, r in enumerate(rows):
        cum_base   += r.baseline_energy_wh
        cum_aiflow += json.loads(r.energy_wh)[band] + r.router_overhead_wh
        if (i + 1) % step == 0 or i == total - 1:
            cumulative.append(CumulativeEnergyPoint(
                requestIndex=i + 1,
                baselineWh=round(cum_base, 2),
                aiflowWh=round(cum_aiflow, 2),
            ))

    # Cap at 20 points for chart
    if len(cumulative) > 20:
        step2 = len(cumulative) // 20
        cumulative = cumulative[::step2][:20]

    return AnalyticsPayload(
        totalRequests=total,
        llmCallsAvoidedCount=avoided_count,
        llmCallsAvoidedPct=avoided_pct,
        energySavedPct=energy_saved_pct,
        co2eSavedPct=co2e_saved_pct,
        qualityRetentionPct=quality_retention,
        pathwayDistribution=pathway_distribution,
        energyByPathwayWh=energy_by_pathway,
        cumulativeEnergy=cumulative,
    )


@app.post("/v1/documents", tags=["documents"])
async def upload_document(file: UploadFile = File(...)):
    """Upload a new document (.txt, .pdf, .doc, .docx) to the corpus and reload the retrieval engine."""
    import os
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".txt", ".pdf", ".doc", ".docx"]:
        raise HTTPException(400, "Only .txt, .pdf, .doc, and .docx files are supported")
    
    from engine.retrieval import CORPUS_DIR, get_retrieval_engine
    import io
    
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    
    content = await file.read()
    text = ""
    
    try:
        if ext == ".txt":
            text = content.decode("utf-8")
        elif ext == ".pdf":
            import pypdf
            pdf_file = io.BytesIO(content)
            reader = pypdf.PdfReader(pdf_file)
            text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        elif ext in [".doc", ".docx"]:
            import docx
            doc_file = io.BytesIO(content)
            doc = docx.Document(doc_file)
            text = "\n".join(para.text for para in doc.paragraphs)
    except Exception as e:
        logger.error(f"Error parsing {file.filename}: {e}")
        raise HTTPException(400, f"Error parsing document: {str(e)}")
        
    if not text.strip():
        raise HTTPException(400, "Document contains no extractable text")
        
    # Save as .txt in corpus directory
    base_name = os.path.splitext(file.filename)[0]
    txt_filename = f"{base_name}.txt"
    file_path = CORPUS_DIR / txt_filename
    
    file_path.write_text(text, encoding="utf-8")
    
    # Reload retrieval engine
    if _sentence_model:
        get_retrieval_engine().load(
            lambda texts: _sentence_model.encode(texts, show_progress_bar=False).tolist()
        )
    
    return {"status": "ok", "filename": txt_filename}


def _empty_analytics() -> AnalyticsPayload:
    return AnalyticsPayload(
        totalRequests=0,
        llmCallsAvoidedCount=0,
        llmCallsAvoidedPct=0.0,
        energySavedPct=0.0,
        co2eSavedPct=0.0,
        qualityRetentionPct=100.0,
        pathwayDistribution=[
            PathwayDistributionItem(pathway=pw, label=m["label"], count=0, color=m["color"])
            for pw, m in _PATHWAY_META.items()
        ],
        energyByPathwayWh=[
            EnergyByPathwayItem(pathway=pw, label=m["label"].split()[0], energyWh=0.0, color=m["color"])
            for pw, m in _PATHWAY_META.items()
        ],
        cumulativeEnergy=[],
    )
