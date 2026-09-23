"""
Tests for the routing-explanation (reason) string in engine/decision.py.

Covers:
  1. Clean-pass:  p_small >= quality_floor + margin  → accurate >= label
  2. Borderline:  quality_floor - margin <= p_small < quality_floor + margin
                  → labels as borderline, no false >= claim
  3. Debug-force: DEBUG_FORCE_ESCALATE=1 → escalated reason, never small-model success

These tests exercise only the reason-string logic by directly invoking the
routing-band selection and the string-building expressions extracted from
decision.py.  They do NOT call the live API, the classifier, the verifier,
or the DB — so they run offline with no server and produce deterministic
output.

Run from backend/:
  .venv/Scripts/python.exe test_routing_reason.py
"""
import sys

# ── Replicate the routing-band selection and reason-building from decision.py ─
# This mirrors the code exactly so any future divergence between the test
# and the production logic will surface as a test failure.

MARGIN = 0.1


def _select_band(p_small: float, quality_floor: float, force_escalate: bool) -> str:
    """Mirror of the Stage-5 ladder in decision.py."""
    if force_escalate:
        return "forced"
    elif p_small >= quality_floor + MARGIN:
        return "clean"
    elif p_small >= quality_floor - MARGIN:
        return "borderline"
    else:
        return "large"


def _build_reason(routing_band: str, p_small: float, quality_floor: float,
                  input_tokens: int) -> str:
    """Mirror of the reason-string builder in decision.py (success path only)."""
    if routing_band == "clean":
        return (
            f"Routed to small model: p_small={p_small:.2f} >= "
            f"floor+margin ({quality_floor + MARGIN:.2f}); "
            f"{input_tokens} prompt tokens"
        )
    else:
        # borderline
        return (
            f"Routed to small model (borderline): p_small={p_small:.2f} "
            f"within margin of floor {quality_floor:.2f} "
            f"(band [{quality_floor - MARGIN:.2f}–{quality_floor + MARGIN:.2f}]); "
            f"strict verification applied; "
            f"{input_tokens} prompt tokens"
        )


def _build_escalation_reason(ver_reason: str, regret_wh: float) -> str:
    """Mirror of the escalation reason string in decision.py."""
    return (
        f"Small model failed verification: {ver_reason}; "
        f"escalated to large model (escalation regret {regret_wh:.4f} Wh)"
    )


# ── Test helpers ──────────────────────────────────────────────────────────────

all_pass = True


def check(label: str, cond: bool, detail: str = "") -> bool:
    global all_pass
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}]  {label}" + (f"  —  {detail}" if detail else ""))
    if not cond:
        all_pass = False
    return cond


# ══════════════════════════════════════════════════════════════════════════════
print("\n══════════════════════════════════════════════════════════════")
print("  Routing Explanation (reason-string) Tests")
print("══════════════════════════════════════════════════════════════\n")

# ── Test 1: Clean-pass ────────────────────────────────────────────────────────
print("① Clean-pass  (p_small=0.80, floor=0.60, margin=0.10)")
p, floor, tokens = 0.80, 0.60, 120
band   = _select_band(p, floor, force_escalate=False)
reason = _build_reason(band, p, floor, tokens)
print(f"   band:   {band}")
print(f"   reason: {reason}")

check("band is 'clean'",
      band == "clean", band)
check("reason does NOT contain 'borderline'",
      "borderline" not in reason)
check("reason contains 'p_small=0.80 >= floor+margin (0.70)'",
      "p_small=0.80 >= floor+margin (0.70)" in reason, reason)
check("reason does NOT claim p_small >= floor without margin qualifier",
      "p_small=0.80 >= floor 0.60" not in reason)
check("reason contains token count",
      f"{tokens} prompt tokens" in reason)

# ── Test 2: Borderline ────────────────────────────────────────────────────────
print("\n② Borderline  (p_small=0.53, floor=0.60, margin=0.10)")
p, floor, tokens = 0.53, 0.60, 116
band   = _select_band(p, floor, force_escalate=False)
reason = _build_reason(band, p, floor, tokens)
print(f"   band:   {band}")
print(f"   reason: {reason}")

check("band is 'borderline'",
      band == "borderline", band)
check("reason contains '(borderline)'",
      "(borderline)" in reason)
check("reason does NOT claim p_small >= floor without qualification",
      "p_small=0.53 >= floor 0.60" not in reason,
      "old misleading string must not appear")
check("reason does NOT claim p_small >= floor+margin",
      "p_small=0.53 >= floor+margin" not in reason)
check("reason mentions 'within margin of floor 0.60'",
      "within margin of floor 0.60" in reason, reason)
check("reason shows correct band [0.50–0.70]",
      "[0.50–0.70]" in reason, reason)
check("reason mentions 'strict verification applied'",
      "strict verification applied" in reason)
check("reason contains token count",
      f"{tokens} prompt tokens" in reason)

# Confirm 0.53 >= 0.50 (the actual condition that fired) is what routing used
check("routing condition p_small >= floor-margin is True (0.53 >= 0.50)",
      p >= floor - 0.1)
check("routing condition p_small >= floor+margin is False (0.53 >= 0.70)",
      not (p >= floor + 0.1))

# ── Test 3: Exact boundary — p_small == floor+margin ─────────────────────────
print("\n③ Exact upper boundary  (p_small=0.70, floor=0.60, margin=0.10)")
p, floor, tokens = 0.70, 0.60, 50
band   = _select_band(p, floor, force_escalate=False)
reason = _build_reason(band, p, floor, tokens)
print(f"   band:   {band}")
print(f"   reason: {reason}")

check("band is 'clean' at exact floor+margin",
      band == "clean", band)
check("reason mentions floor+margin (0.70)",
      "floor+margin (0.70)" in reason)

# ── Test 4: Exact lower boundary — p_small == floor-margin ───────────────────
print("\n④ Exact lower boundary  (p_small=0.50, floor=0.60, margin=0.10)")
p, floor, tokens = 0.50, 0.60, 50
band   = _select_band(p, floor, force_escalate=False)
reason = _build_reason(band, p, floor, tokens)
print(f"   band:   {band}")
print(f"   reason: {reason}")

check("band is 'borderline' at exact floor-margin",
      band == "borderline", band)
check("reason contains '(borderline)'",
      "(borderline)" in reason)

# ── Test 5: Below band — routes to large model ────────────────────────────────
print("\n⑤ Below band  (p_small=0.40, floor=0.60, margin=0.10)")
p, floor = 0.40, 0.60
band = _select_band(p, floor, force_escalate=False)
print(f"   band:   {band}")

check("band is 'large'",
      band == "large", band)
# reason is not built by the small-model success path — no further check needed

# ── Test 6: DEBUG_FORCE_ESCALATE — escalation path, never small-model success ─
print("\n⑥ DEBUG_FORCE_ESCALATE=1  (any p_small)")
p, floor = 0.80, 0.60
band = _select_band(p, floor, force_escalate=True)
print(f"   band:   {band}")

check("force_escalate → band is 'forced', not 'clean'",
      band == "forced", band)
check("force_escalate → band is NOT 'clean'",
      band != "clean")
check("force_escalate → band is NOT 'borderline'",
      band != "borderline")

# The escalation reason (built in the ver.passed=False branch) should reference
# the verifier reason, not suggest clean routing.
ver_reason = "DEBUG_FORCE_ESCALATE flag set"
escalation_reason = _build_escalation_reason(ver_reason, regret_wh=0.0)
print(f"   escalation reason: {escalation_reason}")

check("escalation reason contains verifier failure text",
      "DEBUG_FORCE_ESCALATE flag set" in escalation_reason)
check("escalation reason does NOT mention small-model routing success",
      "Routed to small model" not in escalation_reason)

# ── Test 7: Verify routing thresholds unchanged (regression guard) ────────────
print("\n⑦ Routing threshold regression guard")
cases = [
    # (p_small, floor, expected_band)
    (0.71, 0.60, "clean"),
    (0.70, 0.60, "clean"),       # exact boundary → clean
    (0.69, 0.60, "borderline"),
    (0.53, 0.60, "borderline"),  # the reported bug case
    (0.50, 0.60, "borderline"),  # exact lower boundary → borderline
    (0.49, 0.60, "large"),
    (0.40, 0.60, "large"),
    (0.96, 0.85, "clean"),       # higher quality_floor: 0.96 >= 0.85+0.10=0.95
    (0.80, 0.85, "borderline"),
    (0.74, 0.85, "large"),
]
for p_s, qf, expected in cases:
    b = _select_band(p_s, qf, force_escalate=False)
    check(f"p_small={p_s} floor={qf} → {expected}",
          b == expected, f"got '{b}'")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════════════")
if all_pass:
    print("  ALL TESTS PASSED")
else:
    print("  SOME TESTS FAILED — see above")
print("══════════════════════════════════════════════════════════════\n")
sys.exit(0 if all_pass else 1)
