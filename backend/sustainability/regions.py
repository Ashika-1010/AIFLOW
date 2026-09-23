"""
Region grid-intensity table — values copied verbatim from Frontend/src/mock/regions.ts.
gCO2e per kWh (annual average, Electricity Maps free tier).
"""
from __future__ import annotations
import logging
import os
import httpx

logger = logging.getLogger(__name__)

# Exact values from src/mock/regions.ts  — do NOT change these numbers.
REGIONS: dict[str, int] = {
    "IN": 713,
    "DE": 344,
    "US": 369,
    "FR": 56,
    "SE": 41,
}

# Optional: map region id → Electricity Maps zone code
_EM_ZONES: dict[str, str] = {
    "IN": "IN-NO",
    "DE": "DE",
    "US": "US-CAL-CISO",
    "FR": "FR",
    "SE": "SE",
}


def get_grid_intensity(region: str) -> tuple[int, str]:
    """
    Return (gCO2e_per_kwh, source) where source is 'live' or 'static'.

    If ELECTRICITY_MAPS_API_KEY is set in the environment, attempts a live
    fetch from api.electricitymap.org for the matching zone; falls back to
    the static table on any failure.
    """
    region = region.upper()
    static_value = REGIONS.get(region, REGIONS["US"])

    api_key = os.getenv("ELECTRICITY_MAPS_API_KEY", "").strip()
    if not api_key:
        return static_value, "static"

    zone = _EM_ZONES.get(region)
    if not zone:
        return static_value, "static"

    try:
        resp = httpx.get(
            f"https://api.electricitymap.org/v3/carbon-intensity/latest?zone={zone}",
            headers={"auth-token": api_key},
            timeout=4.0,
        )
        resp.raise_for_status()
        data = resp.json()
        intensity = data.get("carbonIntensity")
        if intensity is not None:
            logger.info("Live grid intensity for %s: %s gCO2e/kWh", region, intensity)
            return int(intensity), "live"
    except Exception as exc:
        logger.warning("Electricity Maps fetch failed for %s: %s — using static value", region, exc)

    return static_value, "static"
