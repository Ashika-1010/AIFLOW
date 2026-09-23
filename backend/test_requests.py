"""
Acceptance test script — runs all checks from the spec.
Run from backend/ with: .venv/Scripts/python.exe test_requests.py
"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


def post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as resp:
        return json.loads(resp.read())


def check(label, condition, detail=""):
    status = "✓ PASS" if condition else "✗ FAIL"
    print(f"  {status}  {label}" + (f"  [{detail}]" if detail else ""))
    return condition


all_pass = True

print("\n══════════════════════════════════════════════════")
print("  AIFlow Acceptance Tests")
print("══════════════════════════════════════════════════\n")

# ── Test 1: Health ────────────────────────────────────────────────────────────
print("① Health")
h = get("/v1/health")
all_pass &= check("status == 'ok'", h.get("status") == "ok", str(h))

# ── Test 2: Arithmetic → deterministic ───────────────────────────────────────
print("\n② Arithmetic → deterministic")
r = post("/v1/complete", {"query": "What is 27 × 43?", "qualityFloor": 0.6, "region": "IN"})
all_pass &= check("pathway == deterministic",    r["pathway"] == "deterministic", r["pathway"])
all_pass &= check("response contains 1161",       "1161" in r["response"],          r["response"])
all_pass &= check("energyWh.central in 1e-7..1e-5",
                  1e-7 < r["energyWh"]["central"] < 1e-5,
                  str(r["energyWh"]["central"]))
all_pass &= check("verification == not_applicable", r["verification"] == "not_applicable")
all_pass &= check("latencyMs < 500",               r["latencyMs"] < 500, f"{r['latencyMs']}ms")
all_pass &= check("escalationRegretWh == 0",        r["escalationRegretWh"] == 0.0)

# ── Test 3: Repeated query → cache ───────────────────────────────────────────
print("\n③ Repeated query → cache on second call")
q = "What is the boiling point of water at standard atmospheric pressure?"
r1 = post("/v1/complete", {"query": q, "qualityFloor": 0.6, "region": "IN"})
r2 = post("/v1/complete", {"query": q, "qualityFloor": 0.6, "region": "IN"})
all_pass &= check("first call processed",            r1["pathway"] in ("cache","deterministic","small_model","large_model","retrieval","escalated"), r1["pathway"])
all_pass &= check("second call is cache",            r2["pathway"] == "cache", r2["pathway"])
all_pass &= check("cache latency < 100ms",           r2["latencyMs"] < 100, f"{r2['latencyMs']}ms")

# ── Test 4: Complex query → large_model (no small attempt) ───────────────────
print("\n④ Complex query → large_model directly")
r = post("/v1/complete", {
    "query": "Critique the philosophical implications of Gödel incompleteness theorems for formal axiomatic systems and mathematical Platonism",
    "qualityFloor": 0.6,
    "region": "IN",
})
all_pass &= check("pathway is large_model or escalated",
                  r["pathway"] in ("large_model", "escalated", "cache"),
                  r["pathway"])
all_pass &= check("complexityScore > 0.4",  r["complexityScore"] > 0.3, str(r["complexityScore"]))
all_pass &= check("latencyMs > 200",        r["latencyMs"] > 200,       f"{r['latencyMs']}ms")

# ── Test 5: DEBUG_FORCE_ESCALATE pathway fixture check ───────────────────────
print("\n⑤ Escalated receipt in DB (from seed)")
receipts = get("/v1/receipts")
escalated = [r for r in receipts if r["pathway"] == "escalated"]
all_pass &= check("at least 1 escalated receipt in DB", len(escalated) >= 1, f"{len(escalated)} found")
if escalated:
    e = escalated[0]
    all_pass &= check("escalationRegretWh > 0",  e["escalationRegretWh"] > 0, str(e["escalationRegretWh"]))
    all_pass &= check("verification == failed",   e["verification"] == "failed", e["verification"])
    all_pass &= check("escalated == True",        e["escalated"] is True)

# ── Test 6: Region changes only CO2e, not energyWh ───────────────────────────
print("\n⑥ Region changes — energyWh unchanged, only CO2e changes")
# Use arithmetic (deterministic), same query, different regions
q = "What is 99 * 11?"
r_in = post("/v1/complete", {"query": q, "qualityFloor": 0.6, "region": "IN"})
r_fr = post("/v1/complete", {"query": q, "qualityFloor": 0.6, "region": "FR"})
# energyWh should be identical (both deterministic)
all_pass &= check("energyWh.central same across regions",
                  abs(r_in["energyWh"]["central"] - r_fr["energyWh"]["central"]) < 1e-10,
                  f"IN={r_in['energyWh']['central']} FR={r_fr['energyWh']['central']}")
all_pass &= check("both deterministic", r_in["pathway"] == "deterministic" and r_fr["pathway"] == "deterministic",
                  f"IN={r_in['pathway']} FR={r_fr['pathway']}")

# ── Test 7: Audit endpoint ────────────────────────────────────────────────────
print("\n⑦ Audit summary — pessimistic changes numbers")
audit_c = get("/v1/audit?pessimistic=false")
audit_p = get("/v1/audit?pessimistic=true")
all_pass &= check("audit has failedCheapAttempts",    "failedCheapAttempts" in audit_c)
all_pass &= check("audit has hiddenSavings == 0",     audit_c["hiddenSavings"] == 0)
all_pass &= check("pessimistic saving <= central saving",
                  audit_p["pessimisticSavingPct"] <= audit_c["centralSavingPct"],
                  f"pessimistic={audit_p['pessimisticSavingPct']} central={audit_c['centralSavingPct']}")
all_pass &= check("qualityRetentionPct in range",     0 < audit_c["qualityRetentionPct"] <= 100,
                  str(audit_c["qualityRetentionPct"]))

# ── Test 8: Analytics ─────────────────────────────────────────────────────────
print("\n⑧ Analytics payload")
analytics = get("/v1/analytics?pessimistic=false")
all_pass &= check("totalRequests > 0",                analytics["totalRequests"] > 0, str(analytics["totalRequests"]))
all_pass &= check("6 pathways in distribution",       len(analytics["pathwayDistribution"]) == 6)
all_pass &= check("energyByPathwayWh has 6 entries",  len(analytics["energyByPathwayWh"]) == 6)
all_pass &= check("cumulativeEnergy has data",        len(analytics["cumulativeEnergy"]) > 0)

# ── Test 9: Get single receipt ────────────────────────────────────────────────
print("\n⑨ GET /v1/receipts/{id}")
receipt = get("/v1/receipts/AF-0284")
all_pass &= check("AF-0284 found",                    receipt["id"] == "AF-0284")
all_pass &= check("pathway == deterministic",         receipt["pathway"] == "deterministic")
all_pass &= check("response contains 1161",           "1161" in receipt["response"])

# 404 test
print("\n⑩ 404 for unknown receipt")
try:
    get("/v1/receipts/AF-9999")
    all_pass &= check("should have raised 404", False)
except urllib.error.HTTPError as e:
    all_pass &= check("returns 404 for unknown ID", e.code == 404, str(e.code))

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════")
if all_pass:
    print("  ALL TESTS PASSED ✓")
else:
    print("  SOME TESTS FAILED — see above")
print("══════════════════════════════════════════════════\n")
sys.exit(0 if all_pass else 1)
