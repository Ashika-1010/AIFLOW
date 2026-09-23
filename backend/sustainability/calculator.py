"""
AIFlow Energy & Carbon Calculator — aiflow-em-1.0
Implements the pitch-deck formula carrying {low, central, high} bands
through every step using the actual low/high coefficients (not scaled ratios).

Formula:
  E_compute_wh = (prompt_tokens/1000)*wh_per_1k_prompt
               + (output_tokens/1000)*wh_per_1k_output
               # or wh_flat for deterministic / cache / retrieval
  E_total_wh   = E_compute_wh * pue
  co2e_g       = (E_total_wh / 1000) * grid_intensity_g_per_kwh
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_PROFILE_PATH = Path(__file__).parent / "energy_profiles.json"

with open(_PROFILE_PATH) as _f:
    _PROFILES = json.load(_f)

Band = Literal["low", "central", "high"]
BANDS: list[Band] = ["low", "central", "high"]


@dataclass
class EnergyBand:
    low: float
    central: float
    high: float

    def to_dict(self) -> dict[str, float]:
        return {"low": self.low, "central": self.central, "high": self.high}


@dataclass
class Co2eBand:
    """
    CO₂e estimate in grams (gCO₂e) for each uncertainty band.

    Formula per band:
        co2e_g = (energy_wh / 1000) × grid_intensity_g_per_kwh

    Values are estimates derived from published benchmark energy coefficients
    and static (or optionally live) grid-intensity data.  They are NOT
    measured emissions.
    """
    low: float
    central: float
    high: float
    grid_intensity_g_per_kwh: int    # the grid intensity used in the calculation
    grid_intensity_source: str       # "static" or "live"

    def to_dict(self) -> dict:
        return {
            "low":                    self.low,
            "central":                self.central,
            "high":                   self.high,
            "gridIntensityGPerKwh":   self.grid_intensity_g_per_kwh,
            "gridIntensitySource":    self.grid_intensity_source,
        }


def _compute_single(
    tier: str,
    band: Band,
    prompt_tokens: int,
    output_tokens: int,
) -> float:
    """Compute energy for a single band."""
    pue = _PROFILES["pue"][band]
    tier_cfg = _PROFILES["tiers"][tier]

    if "wh_flat" in tier_cfg:
        e_compute = tier_cfg["wh_flat"][band]
    else:
        e_compute = (
            (prompt_tokens / 1000.0) * tier_cfg["wh_per_1k_prompt"][band]
            + (output_tokens / 1000.0) * tier_cfg["wh_per_1k_output"][band]
        )
    return e_compute * pue


def compute_energy_band(
    tier: str,
    prompt_tokens: int,
    output_tokens: int,
) -> EnergyBand:
    """
    Return a full {low, central, high} EnergyBand for the given tier.
    Runs the formula three times using the actual coefficient bands.
    """
    return EnergyBand(
        low=_compute_single(tier, "low", prompt_tokens, output_tokens),
        central=_compute_single(tier, "central", prompt_tokens, output_tokens),
        high=_compute_single(tier, "high", prompt_tokens, output_tokens),
    )


def compute_baseline_energy(prompt_tokens: int, output_tokens: int) -> float:
    """
    Always-large-model counterfactual — central band only, as a scalar.
    Used to compute savings.
    """
    return _compute_single("large_model", "central", prompt_tokens, output_tokens)


def compute_co2e(energy_wh: float, grid_intensity_g_per_kwh: int) -> float:
    """gCO2e from Wh and grid intensity."""
    return (energy_wh / 1000.0) * grid_intensity_g_per_kwh


def compute_co2e_band(
    energy: EnergyBand,
    grid_intensity_g_per_kwh: int,
    grid_intensity_source: str = "static",
) -> Co2eBand:
    """
    Convert a three-band EnergyBand (Wh) into a three-band Co2eBand (gCO₂e).

    Each band is computed independently:
        co2e_g = (energy_wh / 1000) × grid_intensity_g_per_kwh

    The low energy band yields the low CO₂e estimate and the high energy band
    yields the high CO₂e estimate — the ordering is preserved because grid
    intensity is a positive scalar.

    Args:
        energy: EnergyBand in Wh.
        grid_intensity_g_per_kwh: Grid carbon intensity in gCO₂e/kWh.
        grid_intensity_source: "static" or "live", for provenance.

    Returns:
        Co2eBand with low/central/high in gCO₂e, plus provenance fields.
    """
    return Co2eBand(
        low=compute_co2e(energy.low, grid_intensity_g_per_kwh),
        central=compute_co2e(energy.central, grid_intensity_g_per_kwh),
        high=compute_co2e(energy.high, grid_intensity_g_per_kwh),
        grid_intensity_g_per_kwh=grid_intensity_g_per_kwh,
        grid_intensity_source=grid_intensity_source,
    )


ROUTER_OVERHEAD_WH: float = _PROFILES["router_overhead_wh"]
