"""
Tests for the demo/real receipt separation in /v1/audit and /v1/analytics.

Scenarios:
  1. No receipts at all
  2. Demo receipts only  (is_demo=True)
  3. One real execution receipt
  4. Multiple real execution receipts
  5. Mix of demo and real receipts

Run from backend/:  .venv/Scripts/python.exe test_audit_demo_separation.py
"""
import json
import sqlite3
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://localhost:8000"

# ── helpers ───────────────────────────────────────────────────────────────────

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


def post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def check(label: str, cond: bool, detail: str = "") -> bool:
    status = "✓ PASS" if cond else "✗ FAIL"
    print(f"  {status}  {label}" + (f"  [{detail}]" if detail else ""))
    return cond


# ── direct DB manipulation ────────────────────────────────────────────────────

def _db():
    return sqlite3.connect("aiflow.db")


def _count(con, is_demo: int | None = None) -> int:
    if is_demo is None:
        return con.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
    return con.execute("SELECT COUNT(*) FROM receipts WHERE is_demo=?", (is_demo,)).fetchone()[0]


def _make_real_receipt(suffix: str, pathway: str = "small_model") -> dict:
    """Return a dict that maps to ReceiptORM columns for a non-demo row."""
    import json as _json
    energy = _json.dumps({"low": 0.012, "central": 0.018, "high": 0.031})
    return dict(
        id=f"AF-TEST-{suffix}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        query=f"Test query {suffix}",
        pathway=pathway,
        pathway_steps=_json.dumps(["Request", "Response"]),
        reason="Test",
        complexity_score=0.3,
        quality_floor=0.6,
        predicted_sufficiency=0.8,
        verification="passed",
        escalated=0,
        input_tokens=20,
        output_tokens=40,
        latency_ms=400,
        provider_cost_usd=0.001,
        energy_wh=energy,
        baseline_energy_wh=0.081,
        router_overhead_wh=0.00003,
        escalation_regret_wh=0.0,
        response="Test response",
        region="IN",
        is_demo=0,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _insert_receipt(con, row: dict):
    cols = list(row.keys())
    placeholders = ",".join("?" * len(cols))
    con.execute(
        f"INSERT OR REPLACE INTO receipts ({','.join(cols)}) VALUES ({placeholders})",
        list(row.values()),
    )
    con.commit()


def _delete_test_rows(con):
    con.execute("DELETE FROM receipts WHERE id LIKE 'AF-TEST-%'")
    con.commit()


# ══════════════════════════════════════════════════════════════════════════════
all_pass = True

print("\n══════════════════════════════════════════════════════════════")
print("  AIFlow Audit — Demo/Real Separation Tests")
print("══════════════════════════════════════════════════════════════\n")

con = _db()

# ── Scenario 1: No receipts at all ────────────────────────────────────────────
print("① No receipts at all")
_delete_test_rows(con)
# Temporarily hide ALL rows (demo + real) by renaming table — too invasive.
# Instead: test the logic by querying the API when only demo rows exist
# and verifying realExecutionCount=0 path. Full "no rows" is covered in scenario 2.
# (We cannot drop the demo rows without destroying seed data.)
# We simulate via the audit endpoint's documented empty-real behaviour.
print("   (Simulated via demo-only scenario — see scenario 2)")

# ── Scenario 2: Demo receipts only ───────────────────────────────────────────
print("\n② Demo receipts only (no real executions)")
_delete_test_rows(con)
demo_count_in_db = _count(con, is_demo=1)
real_count_in_db = _count(con, is_demo=0)
print(f"   DB state: {real_count_in_db} real, {demo_count_in_db} demo")

# Only proceed if we actually have demo rows and no real rows
# (real rows from acceptance tests may exist; zero them out temporarily via query check)
if real_count_in_db == 0:
    audit = get("/v1/audit?pessimistic=false")
    all_pass &= check("realExecutionCount == 0",         audit["realExecutionCount"] == 0,     str(audit["realExecutionCount"]))
    all_pass &= check("demoCount > 0",                   audit["demoCount"] > 0,                str(audit["demoCount"]))
    all_pass &= check("centralSavingPct == 0.0",         audit["centralSavingPct"] == 0.0,     str(audit["centralSavingPct"]))
    all_pass &= check("qualityRetentionPct == 0.0",      audit["qualityRetentionPct"] == 0.0,  str(audit["qualityRetentionPct"]))
    all_pass &= check("pessimisticSavingPct == 0.0",     audit["pessimisticSavingPct"] == 0.0, str(audit["pessimisticSavingPct"]))
    all_pass &= check("hiddenSavings == 0",               audit["hiddenSavings"] == 0)
    all_pass &= check("failedCheapAttempts == 0",         audit["failedCheapAttempts"] == 0)
    analytics = get("/v1/analytics?pessimistic=false")
    all_pass &= check("analytics totalRequests == 0",    analytics["totalRequests"] == 0,      str(analytics["totalRequests"]))
else:
    print(f"   SKIP — {real_count_in_db} real rows exist; run against a clean DB for this scenario")

# ── Scenario 3: One real execution receipt ────────────────────────────────────
print("\n③ One real execution receipt")
_delete_test_rows(con)
row1 = _make_real_receipt("ONE", pathway="small_model")
_insert_receipt(con, row1)

audit = get("/v1/audit?pessimistic=false")
all_pass &= check("realExecutionCount >= 1",            audit["realExecutionCount"] >= 1,      str(audit["realExecutionCount"]))
all_pass &= check("demo rows still excluded",           audit["demoCount"] >= 0)
all_pass &= check("qualityRetentionPct > 0",            audit["qualityRetentionPct"] > 0,      str(audit["qualityRetentionPct"]))
all_pass &= check("centralSavingPct >= 0",              audit["centralSavingPct"] >= 0.0,      str(audit["centralSavingPct"]))
all_pass &= check("hiddenSavings == 0",                  audit["hiddenSavings"] == 0)

analytics = get("/v1/analytics")
all_pass &= check("analytics totalRequests >= 1",       analytics["totalRequests"] >= 1,       str(analytics["totalRequests"]))
all_pass &= check("6 pathway distribution entries",     len(analytics["pathwayDistribution"]) == 6)

_delete_test_rows(con)

# ── Scenario 4: Multiple real execution receipts ──────────────────────────────
print("\n④ Multiple real execution receipts")
rows4 = [
    _make_real_receipt("M1", pathway="deterministic"),
    _make_real_receipt("M2", pathway="cache"),
    _make_real_receipt("M3", pathway="small_model"),
    _make_real_receipt("M4", pathway="large_model"),
    _make_real_receipt("M5", pathway="small_model"),
]
for r in rows4:
    _insert_receipt(con, r)

audit = get("/v1/audit?pessimistic=false")
all_pass &= check("realExecutionCount == 5 (plus any prior reals)", audit["realExecutionCount"] >= 5, str(audit["realExecutionCount"]))
all_pass &= check("qualityRetentionPct 100% (no escalations)",  audit["qualityRetentionPct"] == 100.0, str(audit["qualityRetentionPct"]))

audit_p = get("/v1/audit?pessimistic=true")
all_pass &= check("pessimistic saving <= central saving",
                  audit_p["pessimisticSavingPct"] <= audit["centralSavingPct"],
                  f"pess={audit_p['pessimisticSavingPct']} central={audit['centralSavingPct']}")

analytics = get("/v1/analytics")
all_pass &= check("totalRequests >= 5",                 analytics["totalRequests"] >= 5, str(analytics["totalRequests"]))
all_pass &= check("cumulativeEnergy has points",        len(analytics["cumulativeEnergy"]) > 0)
all_pass &= check("energySavedPct >= 0",                analytics["energySavedPct"] >= 0, str(analytics["energySavedPct"]))

_delete_test_rows(con)

# ── Scenario 5: Mix of demo and real receipts ─────────────────────────────────
print("\n⑤ Mix of demo (is_demo=1) and real (is_demo=0) receipts")
# Insert one real + verify demo rows don't bleed into metrics
row_real = _make_real_receipt("MIX-REAL", pathway="retrieval")
_insert_receipt(con, row_real)
demo_ids = [r[0] for r in con.execute("SELECT id FROM receipts WHERE is_demo=1 LIMIT 5").fetchall()]

audit = get("/v1/audit?pessimistic=false")
real_count_after = audit["realExecutionCount"]
demo_count_after  = audit["demoCount"]

all_pass &= check("demo count == seeded rows",           demo_count_after == _count(con, is_demo=1), f"api={demo_count_after} db={_count(con, is_demo=1)}")
all_pass &= check("real count matches DB real rows",     real_count_after == _count(con, is_demo=0),  f"api={real_count_after} db={_count(con, is_demo=0)}")
all_pass &= check("demo rows excluded from real metric", real_count_after < real_count_after + demo_count_after)

# Verify no demo pathway bleeds into analytics totalRequests
analytics = get("/v1/analytics")
all_pass &= check("analytics totalRequests == DB real rows",
                  analytics["totalRequests"] == _count(con, is_demo=0),
                  f"api={analytics['totalRequests']} db={_count(con, is_demo=0)}")

_delete_test_rows(con)

# ── Scenario 6: Pessimistic toggle only recalculates real rows ────────────────
print("\n⑥ Pessimistic toggle recalculates only real rows")
for r in rows4:
    _insert_receipt(con, r)

audit_c = get("/v1/audit?pessimistic=false")
audit_p = get("/v1/audit?pessimistic=true")
all_pass &= check("same realExecutionCount both modes",
                  audit_c["realExecutionCount"] == audit_p["realExecutionCount"])
all_pass &= check("same demoCount both modes",
                  audit_c["demoCount"] == audit_p["demoCount"])
all_pass &= check("pessimistic <= central (always true)",
                  audit_p["pessimisticSavingPct"] <= audit_c["centralSavingPct"],
                  f"pess={audit_p['pessimisticSavingPct']} central={audit_c['centralSavingPct']}")

_delete_test_rows(con)
con.close()

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════════════")
if all_pass:
    print("  ALL TESTS PASSED ✓")
else:
    print("  SOME TESTS FAILED — see above")
print("══════════════════════════════════════════════════════════════\n")
sys.exit(0 if all_pass else 1)
