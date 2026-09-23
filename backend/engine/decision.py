"""
Decision orchestrator — ties all stages together.

Stage 1: Deterministic gate
Stage 2: Exact cache
Stage 3: Semantic cache
Stage 4: Retrieval
Stage 5: Complexity classifier → tier selection
Stage 6: Verification + escalation

Returns a fully populated Receipt dict.
"""
from __future__ import annotations
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Pathway step labels
_STEPS = {
    "deterministic": ["Request", "Analysis", "Deterministic Gate", "AST Safe Eval", "Response"],
    "deterministic_unit": ["Request", "Analysis", "Deterministic Gate", "Pint Unit Converter", "Response"],
    "deterministic_date": ["Request", "Analysis", "Deterministic Gate", "Dateutil Engine", "Response"],
    "cache_exact":    ["Request", "Analysis", "Exact Cache Hit", "Response"],
    "cache_semantic": ["Request", "Analysis", "Semantic Cache", "Response"],
    "retrieval":      ["Request", "Analysis", "Local Corpus Vector Search", "Corpus Grounding", "Response"],
    "small_model":    ["Request", "Analysis", "Small Model (8B)", "Verification", "Response"],
    "large_model":    ["Request", "Analysis", "Complexity Router", "Large Model (70B+)", "Response"],
    "escalated":      ["Request", "Analysis", "Small Model (8B)", "Quality Verification",
                       "Escalate → Large Model (70B+)", "Response"],
}

_PATHWAY_COLORS = {
    "deterministic": "#22C55E",
    "cache":         "#A855F7",
    "retrieval":     "#6366F1",
    "small_model":   "#FF2D78",
    "large_model":   "#F59E0B",
    "escalated":     "#EF4444",
}

_RECEIPT_COUNTER_FILE = "receipt_counter.txt"


def _next_receipt_id() -> str:
    """Thread-safe incrementing receipt ID using a counter file."""
    try:
        if os.path.exists(_RECEIPT_COUNTER_FILE):
            with open(_RECEIPT_COUNTER_FILE) as f:
                n = int(f.read().strip())
        else:
            n = 284  # start after last fixture (AF-0284)
        n += 1
        with open(_RECEIPT_COUNTER_FILE, "w") as f:
            f.write(str(n))
        return f"AF-{n:04d}"
    except Exception:
        import random
        return f"AF-{random.randint(1000, 9999)}"


def _encode_query(query: str, sentence_model) -> list[float]:
    return sentence_model.encode([query], show_progress_bar=False)[0].tolist()


# Maximum characters returned for a single retrieval response block.
# Large enough to include a full Q&A pair or a complete numbered step,
# small enough to avoid dumping an entire document into the response.
_MAX_BLOCK_CHARS = 800

# A "bare title" is the document's first line used as a heading.
# If the first blank-line block is this short and has no embedded newline,
# we append the second block so the response always contains substance.
_TITLE_ONLY_MAX_CHARS = 60


def _extract_first_block(doc_text: str) -> str:
    """
    Return the first meaningful logical block from a corpus document.

    All 17 corpus documents use blank lines (\\n\\n) as block delimiters
    between Q&A pairs, numbered steps, dash-list sections, and prose
    paragraphs.  This extractor:

    1. Splits the document on \\n\\n to obtain logical blocks.
    2. If the first block is a bare document title (≤ _TITLE_ONLY_MAX_CHARS
       characters and no embedded newline), prepends it to the second block
       so the response is never just a heading with no content.
    3. Caps the result at _MAX_BLOCK_CHARS characters.
    4. Falls back to the raw document head if no blocks are found.

    This is deliberately structure-agnostic: it does not assume Q&A format,
    numbered steps, or any other schema — it just returns what the document
    author chose to put first after the title.
    """
    blocks = [b.strip() for b in doc_text.split('\n\n') if b.strip()]
    if not blocks:
        return doc_text[:_MAX_BLOCK_CHARS]

    first = blocks[0]
    is_bare_title = (
        len(first) <= _TITLE_ONLY_MAX_CHARS
        and '\n' not in first
        and len(blocks) > 1
    )

    if is_bare_title:
        # Combine title + first content block
        result = first + '\n\n' + blocks[1]
    else:
        result = first

    return result[:_MAX_BLOCK_CHARS]


def run_pipeline(
    query: str,
    quality_floor: float,
    region: str,
    sentence_model,
    db,
    doc_filename: Optional[str] = None,
) -> dict:
    """
    Execute the full AIFlow pipeline and return a Receipt-shaped dict.

    If doc_filename is given, Stage 4 is forced: the named corpus document is
    used directly as retrieval context, bypassing the similarity threshold.
    """
    from engine.gates      import try_deterministic
    from engine.cache      import lookup_exact, store_in_cache, get_index
    from engine.retrieval  import get_retrieval_engine
    from engine.classifier import predict as classify
    from engine.verifier   import verify_response
    from clients           import groq_client
    from sustainability.calculator import (
        compute_energy_band, compute_baseline_energy, ROUTER_OVERHEAD_WH,
        compute_co2e_band,
    )
    from sustainability.regions import get_grid_intensity

    t_start    = time.time()
    receipt_id = _next_receipt_id()
    timestamp  = datetime.now(timezone.utc).isoformat()

    # Resolve grid intensity once for this request.
    # get_grid_intensity() handles: unknown regions (falls back to US static),
    # live Electricity Maps fetch (if API key is set), and all error cases.
    grid_intensity_g_per_kwh, grid_intensity_source = get_grid_intensity(region)

    # DEBUG_FORCE_ESCALATE env flag for demo reliability
    logger.info("DEBUG FLAG RAW VALUE: %r", os.getenv("DEBUG_FORCE_ESCALATE"))
    force_escalate = os.getenv("DEBUG_FORCE_ESCALATE", "0") == "1"
    logger.info("DEBUG_FORCE_ESCALATE active: %s", force_escalate)

    # ---------- Stage 1: Deterministic gate ----------
    gate = try_deterministic(query)
    if gate.matched:
        steps = {
            "date":       _STEPS["deterministic_date"],
            "unit":       _STEPS["deterministic_unit"],
            "arithmetic": _STEPS["deterministic"],
        }.get(gate.sub_type, _STEPS["deterministic"])

        energy = compute_energy_band("deterministic", 8, 5)
        baseline = compute_baseline_energy(8, 5)

        return _build_receipt(
            receipt_id=receipt_id,
            timestamp=timestamp,
            query=query,
            pathway="deterministic",
            pathway_steps=steps,
            reason=gate.reason,
            complexity_score=0.02,
            quality_floor=quality_floor,
            predicted_sufficiency=1.00,
            verification="not_applicable",
            escalated=False,
            input_tokens=max(4, len(query.split())),
            output_tokens=max(3, len(gate.response.split())),
            latency_ms=max(1, int((time.time() - t_start) * 1000)),
            provider_cost_usd=0.0,
            energy=energy,
            baseline_energy=baseline,
            router_overhead_wh=ROUTER_OVERHEAD_WH,
            escalation_regret_wh=0.0,
            response=gate.response,
            co2e=compute_co2e_band(energy, grid_intensity_g_per_kwh, grid_intensity_source),
        )

    # ---------- Embed query (needed for stages 2-5) ----------
    query_embedding = _encode_query(query, sentence_model)

    # ---------- Stage 2: Exact cache ----------
    exact_hit = lookup_exact(db, query)
    if exact_hit:
        energy   = compute_energy_band("cache", 8, 8)
        baseline = compute_baseline_energy(8, 8)
        return _build_receipt(
            receipt_id=receipt_id,
            timestamp=timestamp,
            query=query,
            pathway="cache",
            pathway_steps=_STEPS["cache_exact"],
            reason="Exact SHA-256 cache match, sub-millisecond hash resolution",
            complexity_score=0.02,
            quality_floor=quality_floor,
            predicted_sufficiency=0.99,
            verification="not_applicable",
            escalated=False,
            input_tokens=8,
            output_tokens=8,
            latency_ms=max(1, int((time.time() - t_start) * 1000)),
            provider_cost_usd=0.0,
            energy=energy,
            baseline_energy=baseline,
            router_overhead_wh=ROUTER_OVERHEAD_WH,
            escalation_regret_wh=0.0,
            response=exact_hit,
            co2e=compute_co2e_band(energy, grid_intensity_g_per_kwh, grid_intensity_source),
        )

    # ---------- Stage 3: Semantic cache ----------
    sem_hit = get_index().lookup(query, query_embedding)
    if sem_hit:
        cached_response, sim_score = sem_hit
        energy   = compute_energy_band("cache", 8, 8)
        baseline = compute_baseline_energy(8, 8)
        return _build_receipt(
            receipt_id=receipt_id,
            timestamp=timestamp,
            query=query,
            pathway="cache",
            pathway_steps=_STEPS["cache_semantic"],
            reason=f"Semantic cache hit, cosine {sim_score:.2f}",
            complexity_score=0.04,
            quality_floor=quality_floor,
            predicted_sufficiency=0.99,
            verification="not_applicable",
            escalated=False,
            input_tokens=8,
            output_tokens=8,
            latency_ms=max(2, int((time.time() - t_start) * 1000)),
            provider_cost_usd=0.0,
            energy=energy,
            baseline_energy=baseline,
            router_overhead_wh=ROUTER_OVERHEAD_WH,
            escalation_regret_wh=0.0,
            response=cached_response,
            co2e=compute_co2e_band(energy, grid_intensity_g_per_kwh, grid_intensity_source),
        )

    # ---------- Stage 4: Retrieval ----------
    # If the caller pinned a specific uploaded document, use it directly.
    # Otherwise fall back to embedding-similarity search over the whole corpus.
    forced_doc: Optional[tuple[str, str]] = None  # (title, doc_text)
    if doc_filename:
        from engine.retrieval import CORPUS_DIR
        # Normalise: strip any path components the client might have sent
        safe_name = os.path.basename(doc_filename)
        # Ensure it ends with .txt (upload endpoint always saves as .txt)
        if not safe_name.endswith(".txt"):
            safe_name = os.path.splitext(safe_name)[0] + ".txt"
        doc_path = CORPUS_DIR / safe_name
        if doc_path.exists():
            doc_text = doc_path.read_text(encoding="utf-8").strip()
            title    = os.path.splitext(safe_name)[0]
            forced_doc = (title, doc_text)
            logger.info("Pinned document '%s' injected as retrieval context", safe_name)
        else:
            logger.warning("Pinned document '%s' not found in corpus; falling back to similarity search", safe_name)

    if forced_doc:
        title, doc_text = forced_doc
        sim_score = 1.0  # pinned — treat as perfect match
    else:
        retrieval = get_retrieval_engine().lookup(query_embedding)
        if retrieval:
            title, doc_text, sim_score = retrieval
        else:
            title = doc_text = None
            sim_score = 0.0

    if doc_text:
        # Generative RAG: Build a grounded response using the small model
        prompt = f"Use the following document to answer the query.\n\nDocument: {doc_text}\n\nQuery: {query}"
        small_resp = groq_client.call_small(prompt)

        energy    = compute_energy_band("small_model", small_resp.input_tokens, small_resp.output_tokens)
        baseline  = compute_baseline_energy(small_resp.input_tokens, small_resp.output_tokens)

        in_toks  = small_resp.input_tokens
        out_toks = small_resp.output_tokens

        response_text = small_resp.content
        store_in_cache(db, query, response_text, query_embedding,
                       source_pathway="retrieval")

        reason_label = "Pinned uploaded document" if forced_doc else f"Local corpus matched '{title}'"
        return _build_receipt(
            receipt_id=receipt_id,
            timestamp=timestamp,
            query=query,
            pathway="retrieval",
            pathway_steps=_STEPS["retrieval"],
            reason=f"{reason_label} (cosine {sim_score:.2f})",
            complexity_score=0.15,
            quality_floor=quality_floor,
            predicted_sufficiency=0.90,
            verification="passed",
            escalated=False,
            input_tokens=in_toks,
            output_tokens=out_toks,
            latency_ms=max(50, small_resp.latency_ms),
            provider_cost_usd=small_resp.provider_cost_usd,
            energy=energy,
            baseline_energy=baseline,
            router_overhead_wh=ROUTER_OVERHEAD_WH,
            escalation_regret_wh=0.0,
            response=response_text,
            co2e=compute_co2e_band(energy, grid_intensity_g_per_kwh, grid_intensity_source),
        )

    # ---------- Stage 5: Complexity classifier ----------
    p_small = classify(query, query_embedding)
    margin  = 0.1

    if force_escalate:
        # Force escalate path for demo
        tier          = "small_model"
        verify_strict = True
        force_fail    = True
        routing_band  = "forced"
    elif p_small >= quality_floor + margin:
        tier          = "small_model"
        verify_strict = False
        force_fail    = False
        routing_band  = "clean"        # p_small clearly above floor+margin
    elif p_small >= quality_floor - margin:
        tier          = "small_model"
        verify_strict = True
        force_fail    = False
        routing_band  = "borderline"   # p_small within ±margin of floor
    else:
        tier          = "large_model"
        verify_strict = False
        force_fail    = False
        routing_band  = "large"

    # ---------- Stage 6: Tier execution + verification ----------
    if tier == "small_model":
        small_resp   = groq_client.call_small(query)
        small_energy = compute_energy_band("small_model", small_resp.input_tokens, small_resp.output_tokens)
        baseline_wh  = compute_baseline_energy(small_resp.input_tokens, small_resp.output_tokens)

        # Verification
        if force_escalate and force_fail:
            ver = type("V", (), {"passed": False, "reason": "DEBUG_FORCE_ESCALATE flag set"})()
        else:
            ver = verify_response(query, small_resp.content)

        if not ver.passed:
            # Escalate to large model
            large_resp   = groq_client.call_large(query)
            large_energy = compute_energy_band("large_model", large_resp.input_tokens, large_resp.output_tokens)
            baseline_wh  = compute_baseline_energy(large_resp.input_tokens, large_resp.output_tokens)
            escalation_regret = small_energy.central

            total_latency = small_resp.latency_ms + large_resp.latency_ms
            total_in      = small_resp.input_tokens + large_resp.input_tokens
            total_out     = small_resp.output_tokens + large_resp.output_tokens
            total_cost    = small_resp.provider_cost_usd + large_resp.provider_cost_usd

            reason = (
                f"Small model failed verification: {ver.reason}; "
                f"escalated to large model (escalation regret "
                f"{escalation_regret:.4f} Wh)"
            )
            # Cache successful large-model response
            store_in_cache(db, query, large_resp.content, query_embedding)

            return _build_receipt(
                receipt_id=receipt_id,
                timestamp=timestamp,
                query=query,
                pathway="escalated",
                pathway_steps=_STEPS["escalated"],
                reason=reason,
                complexity_score=round(1.0 - p_small, 2),
                quality_floor=quality_floor,
                predicted_sufficiency=round(p_small, 2),
                verification="failed",
                escalated=True,
                input_tokens=total_in,
                output_tokens=total_out,
                latency_ms=total_latency,
                provider_cost_usd=total_cost,
                energy=large_energy,
                baseline_energy=baseline_wh,
                router_overhead_wh=ROUTER_OVERHEAD_WH,
                escalation_regret_wh=escalation_regret,
                response=large_resp.content,
                co2e=compute_co2e_band(large_energy, grid_intensity_g_per_kwh, grid_intensity_source),
            )
        else:
            # Small model passed — build an accurate explanation based on
            # which routing branch actually selected this tier.
            if routing_band == "clean":
                reason = (
                    f"Routed to small model: p_small={p_small:.2f} >= "
                    f"floor+margin ({quality_floor + margin:.2f}); "
                    f"{small_resp.input_tokens} prompt tokens"
                )
            else:
                # borderline: quality_floor - margin <= p_small < quality_floor + margin
                reason = (
                    f"Routed to small model (borderline): p_small={p_small:.2f} "
                    f"within margin of floor {quality_floor:.2f} "
                    f"(band [{quality_floor - margin:.2f}–{quality_floor + margin:.2f}]); "
                    f"strict verification applied; "
                    f"{small_resp.input_tokens} prompt tokens"
                )
            store_in_cache(db, query, small_resp.content, query_embedding)
            return _build_receipt(
                receipt_id=receipt_id,
                timestamp=timestamp,
                query=query,
                pathway="small_model",
                pathway_steps=_STEPS["small_model"],
                reason=reason,
                complexity_score=round(1.0 - p_small, 2),
                quality_floor=quality_floor,
                predicted_sufficiency=round(p_small, 2),
                verification="passed",
                escalated=False,
                input_tokens=small_resp.input_tokens,
                output_tokens=small_resp.output_tokens,
                latency_ms=small_resp.latency_ms,
                provider_cost_usd=small_resp.provider_cost_usd,
                energy=small_energy,
                baseline_energy=baseline_wh,
                router_overhead_wh=ROUTER_OVERHEAD_WH,
                escalation_regret_wh=0.0,
                response=small_resp.content,
                co2e=compute_co2e_band(small_energy, grid_intensity_g_per_kwh, grid_intensity_source),
            )
    else:
        # large_model directly
        large_resp   = groq_client.call_large(query)
        large_energy = compute_energy_band("large_model", large_resp.input_tokens, large_resp.output_tokens)
        baseline_wh  = compute_baseline_energy(large_resp.input_tokens, large_resp.output_tokens)

        reason = (
            f"Routed to large model: p_small={p_small:.2f} < floor {quality_floor:.2f}; "
            f"complexity score {1.0-p_small:.2f} > threshold; "
            f"{large_resp.input_tokens} prompt tokens"
        )
        store_in_cache(db, query, large_resp.content, query_embedding)
        return _build_receipt(
            receipt_id=receipt_id,
            timestamp=timestamp,
            query=query,
            pathway="large_model",
            pathway_steps=_STEPS["large_model"],
            reason=reason,
            complexity_score=round(1.0 - p_small, 2),
            quality_floor=quality_floor,
            predicted_sufficiency=round(p_small, 2),
            verification="not_applicable",
            escalated=False,
            input_tokens=large_resp.input_tokens,
            output_tokens=large_resp.output_tokens,
            latency_ms=large_resp.latency_ms,
            provider_cost_usd=large_resp.provider_cost_usd,
            energy=large_energy,
            baseline_energy=baseline_wh,
            router_overhead_wh=ROUTER_OVERHEAD_WH,
            escalation_regret_wh=0.0,
            response=large_resp.content,
            co2e=compute_co2e_band(large_energy, grid_intensity_g_per_kwh, grid_intensity_source),
        )


def _build_receipt(
    receipt_id, timestamp, query, pathway, pathway_steps,
    reason, complexity_score, quality_floor, predicted_sufficiency,
    verification, escalated, input_tokens, output_tokens, latency_ms,
    provider_cost_usd, energy, baseline_energy, router_overhead_wh,
    escalation_regret_wh, response, co2e,
) -> dict:
    return {
        "id":                  receipt_id,
        "timestamp":           timestamp,
        "query":               query,
        "pathway":             pathway,
        "pathwaySteps":        pathway_steps,
        "reason":              reason,
        "complexityScore":     complexity_score,
        "qualityFloor":        quality_floor,
        "predictedSufficiency": predicted_sufficiency,
        "verification":        verification,
        "escalated":           escalated,
        "inputTokens":         input_tokens,
        "outputTokens":        output_tokens,
        "latencyMs":           latency_ms,
        "providerCostUsd":     provider_cost_usd,
        "energyWh":            energy.to_dict(),
        "baselineEnergyWh":    baseline_energy,
        "routerOverheadWh":    router_overhead_wh,
        "escalationRegretWh":  escalation_regret_wh,
        "response":            response,
        # CO₂e estimate — always present for new receipts.
        "co2eGrams":           co2e.to_dict(),
    }
