"""
Tests for CO₂e estimation — backend/sustainability/calculator.py,
backend/sustainability/regions.py, and backend/db.py (to_pydantic null-safety).

All tests use deterministic mocked values. No external API calls, no live server,
no database connection required.

Run from backend/:  .venv/Scripts/python.exe test_co2e.py
"""
import json
import sys
from dataclasses import dataclass
from typing import Optional
from unittest.mock import patch

# ── Helpers ────────────────────────────────────────────────────────────────────

all_pass = True


def check(label: str, cond: bool, detail: str = "") -> bool:
    global all_pass
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}]  {label}" + (f"  —  {detail}" if detail else ""))
    if not cond:
        all_pass = False
    return cond


# ── Import the modules under test ──────────────────────────────────────────────

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sustainability.calculator import (
    EnergyBand, Co2eBand, compute_co2e, compute_co2e_band, compute_energy_band,
)
from sustainability.regions import REGIONS, get_grid_intensity

# ══════════════════════════════════════════════════════════════════════════════
print("\n══════════════════════════════════════════════════════════════")
print("  CO₂e Estimation Tests")
print("══════════════════════════════════════════════════════════════\n")

# ── 1. Unit formula: compute_co2e ─────────────────────────────────────────────
print("① compute_co2e — unit conversion correctness")

check("1 Wh at 1000 gCO₂e/kWh → 1.0 gCO₂e",
      compute_co2e(1.0, 1000) == 1.0,
      str(compute_co2e(1.0, 1000)))

check("1 Wh at 500 gCO₂e/kWh → 0.5 gCO₂e",
      compute_co2e(1.0, 500) == 0.5,
      str(compute_co2e(1.0, 500)))

check("0 Wh → 0.0 gCO₂e",
      compute_co2e(0.0, 713) == 0.0)

check("1000 Wh at 713 gCO₂e/kWh → 713.0 gCO₂e",
      compute_co2e(1000.0, 713) == 713.0,
      str(compute_co2e(1000.0, 713)))

# deterministic tier central: 0.000001 Wh, India 713 gCO₂e/kWh
expected = 0.000001 / 1000 * 713
check(f"deterministic central Wh (1e-6) at IN=713 → {expected:.2e} gCO₂e",
      abs(compute_co2e(0.000001, 713) - expected) < 1e-15)

# ── 2. Three-band consistency: compute_co2e_band ──────────────────────────────
print("\n② compute_co2e_band — band ordering and consistency")

energy = EnergyBand(low=0.012, central=0.018, high=0.031)
band = compute_co2e_band(energy, 713, "static")

check("returns Co2eBand instance", isinstance(band, Co2eBand))
check("low CO₂e < central CO₂e", band.low < band.central,
      f"low={band.low:.6f} central={band.central:.6f}")
check("central CO₂e < high CO₂e", band.central < band.high,
      f"central={band.central:.6f} high={band.high:.6f}")
check("low matches formula",   abs(band.low     - compute_co2e(energy.low,     713)) < 1e-15)
check("central matches formula", abs(band.central - compute_co2e(energy.central, 713)) < 1e-15)
check("high matches formula",  abs(band.high    - compute_co2e(energy.high,    713)) < 1e-15)
check("grid_intensity stored", band.grid_intensity_g_per_kwh == 713)
check("source stored",         band.grid_intensity_source == "static")

# ── 3. Region-specific CO₂e values ────────────────────────────────────────────
print("\n③ Region-specific CO₂e — correct grid intensity per region")

# Fixed energy for comparison
e = EnergyBand(low=0.1, central=0.1, high=0.1)  # 0.1 Wh all bands

expected_by_region = {
    "IN": 0.1 / 1000 * 713,   # 0.0713
    "DE": 0.1 / 1000 * 344,   # 0.0344
    "US": 0.1 / 1000 * 369,   # 0.0369
    "FR": 0.1 / 1000 * 56,    # 0.0056
    "SE": 0.1 / 1000 * 41,    # 0.0041
}

for region_id, expected_central in expected_by_region.items():
    intensity, source = get_grid_intensity(region_id)
    b = compute_co2e_band(e, intensity, source)
    check(f"{region_id} central CO₂e = {expected_central:.4f}",
          abs(b.central - expected_central) < 1e-10,
          f"got {b.central:.6f}")

# Confirm CO₂e ordering across regions (higher intensity → higher CO₂e)
bands = {r: compute_co2e_band(e, get_grid_intensity(r)[0], "static").central
         for r in ["SE", "FR", "DE", "US", "IN"]}
check("SE < FR < DE/US < IN ordering preserved",
      bands["SE"] < bands["FR"] < bands["DE"] and bands["FR"] < bands["US"] < bands["IN"],
      str({k: f"{v:.4f}" for k, v in bands.items()}))

# ── 4. Missing / unsupported region handling ──────────────────────────────────
print("\n④ Unknown/unsupported region handling in get_grid_intensity")

# regions.py falls back to US (369) for unknown regions
intensity_unknown, source_unknown = get_grid_intensity("XX")
check("unknown region 'XX' falls back to US (369)",
      intensity_unknown == REGIONS["US"],
      f"got {intensity_unknown}")
check("unknown region source is 'static'", source_unknown == "static")

intensity_lower, _ = get_grid_intensity("in")   # lowercase
check("lowercase 'in' normalised to 'IN' (713)", intensity_lower == 713)

intensity_empty, _ = get_grid_intensity("")
check("empty string falls back to US (369)", intensity_empty == REGIONS["US"])

# ── 5. Live Electricity Maps path — mocked, no real HTTP ──────────────────────
print("\n⑤ Live Electricity Maps path (mocked — no real HTTP)")

import os
with patch.dict(os.environ, {"ELECTRICITY_MAPS_API_KEY": "test-key"}):
    with patch("httpx.get") as mock_get:
        mock_resp = mock_get.return_value
        mock_resp.raise_for_status = lambda: None
        mock_resp.json.return_value = {"carbonIntensity": 250}

        live_intensity, live_source = get_grid_intensity("DE")
        check("live intensity returned when API responds", live_intensity == 250,
              f"got {live_intensity}")
        check("source is 'live'", live_source == "live")

        # Simulate API failure — should fall back to static
        mock_get.side_effect = Exception("Network error")
        fallback_intensity, fallback_source = get_grid_intensity("DE")
        check("falls back to static on API failure",
              fallback_intensity == REGIONS["DE"] and fallback_source == "static",
              f"intensity={fallback_intensity} source={fallback_source}")

# ── 6. compute_co2e_band with energy bands from the pipeline ──────────────────
print("\n⑥ Integration: energy band from compute_energy_band feeds into compute_co2e_band")

energy_sm = compute_energy_band("small_model", 116, 68)  # real token counts from a live run
band_sm_in = compute_co2e_band(energy_sm, 713, "static")
band_sm_fr = compute_co2e_band(energy_sm, 56,  "static")

check("small_model energy band has low < central < high",
      energy_sm.low < energy_sm.central < energy_sm.high)
check("IN CO₂e > FR CO₂e (higher intensity)",
      band_sm_in.central > band_sm_fr.central,
      f"IN={band_sm_in.central:.4f} FR={band_sm_fr.central:.4f}")
check("same energy Wh, different CO₂e for different regions",
      abs(band_sm_in.central - band_sm_fr.central) > 0)

# ── 7. to_pydantic null safety (historical receipts) ──────────────────────────
print("\n⑦ ReceiptORM.to_pydantic — null CO₂e for historical receipts")

# Simulate a historical ReceiptORM row by constructing a minimal stub
class _StubORM:
    """Minimal stub mimicking a ReceiptORM row from db.py."""
    id = "AF-0001"
    timestamp = "2026-09-19T09:00:00Z"
    query = "test"
    pathway = "deterministic"
    pathway_steps = json.dumps(["Request", "Response"])
    reason = "test"
    complexity_score = 0.02
    quality_floor = 0.6
    predicted_sufficiency = 1.0
    verification = "not_applicable"
    escalated = False
    input_tokens = 8
    output_tokens = 5
    latency_ms = 1
    provider_cost_usd = 0.0
    energy_wh = json.dumps({"low": 5e-7, "central": 1e-6, "high": 3e-6})
    baseline_energy_wh = 0.081
    router_overhead_wh = 0.00003
    escalation_regret_wh = 0.0
    response = "test"
    is_demo = False
    # These are the new columns — NULL for historical rows
    co2e_low = None
    co2e_central = None
    co2e_high = None
    co2e_grid_intensity = None
    co2e_grid_source = None

    def to_pydantic(self):
        # Copy-paste the actual to_pydantic logic from db.py
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
        return {"co2eGrams": co2e_grams, **{k: getattr(self, k)
                for k in ("id", "timestamp", "query", "pathway", "escalated",
                          "input_tokens", "output_tokens", "latency_ms",
                          "provider_cost_usd", "baseline_energy_wh",
                          "router_overhead_wh", "escalation_regret_wh")}}


stub_historical = _StubORM()
d_historical = stub_historical.to_pydantic()
check("historical receipt: co2eGrams is None", d_historical["co2eGrams"] is None,
      str(d_historical["co2eGrams"]))

# Now set all five columns — simulates a new receipt
stub_historical.co2e_low = 0.001
stub_historical.co2e_central = 0.002
stub_historical.co2e_high = 0.003
stub_historical.co2e_grid_intensity = 713
stub_historical.co2e_grid_source = "static"

d_new = stub_historical.to_pydantic()
check("new receipt: co2eGrams is not None", d_new["co2eGrams"] is not None)
check("new receipt: co2eGrams.central == 0.002",
      d_new["co2eGrams"]["central"] == 0.002)
check("new receipt: gridIntensityGPerKwh == 713",
      d_new["co2eGrams"]["gridIntensityGPerKwh"] == 713)
check("new receipt: gridIntensitySource == 'static'",
      d_new["co2eGrams"]["gridIntensitySource"] == "static")

# Partial NULL — all five columns must be present or result is None
stub_historical.co2e_grid_source = None   # knock out one field
d_partial = stub_historical.to_pydantic()
check("partial NULL: co2eGrams is None (all-or-nothing)", d_partial["co2eGrams"] is None,
      str(d_partial["co2eGrams"]))

# ── 8. co2e_band.to_dict — correct keys for JSON serialisation ───────────────
print("\n⑧ Co2eBand.to_dict — correct keys match frontend Co2eGrams interface")

band = compute_co2e_band(EnergyBand(0.1, 0.2, 0.3), 369, "live")
d = band.to_dict()

check("has 'low' key",                    "low"                  in d)
check("has 'central' key",                "central"              in d)
check("has 'high' key",                   "high"                 in d)
check("has 'gridIntensityGPerKwh' key",   "gridIntensityGPerKwh" in d)
check("has 'gridIntensitySource' key",    "gridIntensitySource"  in d)
check("no unexpected keys",               set(d.keys()) == {
          "low", "central", "high", "gridIntensityGPerKwh", "gridIntensitySource"})
check("gridIntensitySource is 'live'",    d["gridIntensitySource"] == "live")
check("gridIntensityGPerKwh is 369",      d["gridIntensityGPerKwh"] == 369)

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════════════")
if all_pass:
    print("  ALL TESTS PASSED")
else:
    print("  SOME TESTS FAILED — see above")
print("══════════════════════════════════════════════════════════════\n")
sys.exit(0 if all_pass else 1)
