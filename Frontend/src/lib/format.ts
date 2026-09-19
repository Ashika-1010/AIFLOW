/**
 * Unified formatting functions for all metrics in AIFlow.
 * Rule: Every number displayed must carry its unit. Never render a bare float.
 */

/**
 * Formats energy in Watt-hours (Wh).
 * For values below 0.0005 Wh (negligible/CPU tier), returns "~0.000 Wh".
 */
export function formatWh(val: number): string {
  if (val === 0) return '0.000 Wh';
  if (val > 0 && val < 0.0005) {
    return '~0.000 Wh';
  }
  return `${val.toFixed(3)} Wh`;
}

/**
 * Formats carbon emissions in grams of CO₂ equivalent (gCO₂e).
 */
export function formatCO2e(val: number): string {
  if (val === 0) return '0.000 gCO₂e';
  if (val > 0 && val < 0.0005) {
    return '~0.000 gCO₂e';
  }
  if (val < 0.01) {
    return `${val.toFixed(3)} gCO₂e`;
  }
  return `${val.toFixed(3)} gCO₂e`;
}

/**
 * Formats carbon range (e.g. "0.009 – 0.022 gCO₂e")
 */
export function formatCO2eRange(low: number, high: number): string {
  const lowStr = low < 0.0005 ? '~0.000' : low.toFixed(3);
  const highStr = high < 0.0005 ? '~0.000' : high.toFixed(3);
  return `${lowStr} – ${highStr} gCO₂e`;
}

/**
 * Formats latency (2 ms / 421 ms / 1.4 s).
 */
export function formatLatency(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)} ms`;
  }
  return `${(ms / 1000).toFixed(1)} s`;
}

/**
 * Formats provider cost in USD (4 decimals, e.g. "$0.0008").
 */
export function formatUsd(usd: number): string {
  return `$${usd.toFixed(4)}`;
}

/**
 * Formats percentages (e.g. "31%", "98.7%").
 */
export function formatPct(pct: number, decimals: number = 0): string {
  if (decimals === 0) {
    return `${Math.round(pct)}%`;
  }
  return `${pct.toFixed(decimals)}%`;
}

/**
 * Formats integer token counts.
 */
export function formatTokens(count: number): string {
  return `${count.toLocaleString()} tokens`;
}

/**
 * Formats grid intensity (e.g. "713 gCO₂e/kWh").
 */
export function formatGridIntensity(intensity: number): string {
  return `${intensity} gCO₂e/kWh`;
}
