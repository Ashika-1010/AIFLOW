"""
SQLAlchemy engine, session, and ORM models.
Database: SQLite at ./aiflow.db (relative to CWD when uvicorn is run).
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Boolean, Column, Float, Integer, String, Text,
    DateTime, create_engine, event
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

DB_PATH = Path("aiflow.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Enable WAL mode for better concurrent read/write
@event.listens_for(engine, "connect")
def _set_wal(dbapi_connection, _):
    dbapi_connection.execute("PRAGMA journal_mode=WAL")
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI dependency: yields a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    pass


class ReceiptORM(Base):
    __tablename__ = "receipts"

    id = Column(String, primary_key=True, index=True)
    timestamp = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    pathway = Column(String, nullable=False)
    pathway_steps = Column(Text, nullable=False)   # JSON list
    reason = Column(Text, nullable=False)
    complexity_score = Column(Float, nullable=False)
    quality_floor = Column(Float, nullable=False)
    predicted_sufficiency = Column(Float, nullable=False)
    verification = Column(String, nullable=False)
    escalated = Column(Boolean, nullable=False, default=False)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    provider_cost_usd = Column(Float, nullable=False)
    energy_wh = Column(Text, nullable=False)   # JSON {low, central, high}
    baseline_energy_wh = Column(Float, nullable=False)
    router_overhead_wh = Column(Float, nullable=False)
    escalation_regret_wh = Column(Float, nullable=False)
    response = Column(Text, nullable=False)
    region = Column(String, nullable=False, default="IN")
    # is_demo=True rows come from seed_demo.py and are NEVER included in audit/analytics metrics.
    # They are shown in the receipts ledger with a clear DEMO label.
    is_demo = Column(Boolean, nullable=False, default=False, server_default="0")
    # CO₂e estimate columns — nullable so historical receipts remain valid.
    # Populated for all receipts created after the CO₂e tracking feature was added.
    co2e_low = Column(Float, nullable=True)        # gCO₂e, low band
    co2e_central = Column(Float, nullable=True)    # gCO₂e, central band
    co2e_high = Column(Float, nullable=True)       # gCO₂e, high band
    co2e_grid_intensity = Column(Integer, nullable=True)  # gCO₂e/kWh used
    co2e_grid_source = Column(String, nullable=True)      # "static" or "live"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_pydantic(self) -> dict:
        # Build co2eGrams only when all five CO₂e columns are present.
        # Historical and demo receipts have NULL co2e columns — return None
        # rather than fabricating a value.
        if (self.co2e_low is not None
                and self.co2e_central is not None
                and self.co2e_high is not None
                and self.co2e_grid_intensity is not None
                and self.co2e_grid_source is not None):
            co2e_grams = {
                "low":                  self.co2e_low,
                "central":              self.co2e_central,
                "high":                 self.co2e_high,
                "gridIntensityGPerKwh": self.co2e_grid_intensity,
                "gridIntensitySource":  self.co2e_grid_source,
            }
        else:
            co2e_grams = None

        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "query": self.query,
            "pathway": self.pathway,
            "pathwaySteps": json.loads(self.pathway_steps),
            "reason": self.reason,
            "complexityScore": self.complexity_score,
            "qualityFloor": self.quality_floor,
            "predictedSufficiency": self.predicted_sufficiency,
            "verification": self.verification,
            "escalated": self.escalated,
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "latencyMs": self.latency_ms,
            "providerCostUsd": self.provider_cost_usd,
            "energyWh": json.loads(self.energy_wh),
            "baselineEnergyWh": self.baseline_energy_wh,
            "routerOverheadWh": self.router_overhead_wh,
            "escalationRegretWh": self.escalation_regret_wh,
            "response": self.response,
            # Passed through so the frontend can label demo rows in the ledger.
            "isDemo": bool(self.is_demo),
            # CO₂e estimate — None for historical/demo receipts without CO₂e data.
            "co2eGrams": co2e_grams,
        }


class CacheEntryORM(Base):
    __tablename__ = "cache_exact"

    hash = Column(String, primary_key=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)   # JSON float list
    # source_pathway: "retrieval", "model", or "seed".
    # Retrieval entries are invalidated when the corpus version changes.
    source_pathway = Column(String, nullable=True)
    # corpus_version: hex digest of corpus file mtimes+sizes at write time.
    # NULL for pre-existing entries; treated as stale if a corpus version is active.
    corpus_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ClassifierMetricsORM(Base):
    __tablename__ = "classifier_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    accuracy = Column(Float, nullable=False)
    auc = Column(Float, nullable=False)
    n_train = Column(Integer, nullable=False)
    n_test = Column(Integer, nullable=False)
    trained_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
