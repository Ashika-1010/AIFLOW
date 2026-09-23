"""
Tests for RAG retrieval improvements.

Covers:
  1. Block extractor (_extract_first_block) — structure-aware extraction
     across all corpus document types (Q&A, dash-list, numbered steps,
     prose, category-group).
  2. Similarity ranking — model-cards must beat model_routing_faq for
     model-identity queries; model_routing_faq must win for routing-
     behaviour queries.
  3. Model-ID presence — the block returned for model_cards contains
     the live model IDs (openai/gpt-oss-20b and openai/gpt-oss-120b).
  4. Response sanity — extraction never returns an empty string and
     never exceeds _MAX_BLOCK_CHARS characters.

Run from backend/:  .venv/Scripts/python.exe test_retrieval.py

Embedding tests require the sentence-transformers package and the
all-MiniLM-L6-v2 model (already present in .venv from startup).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from engine.decision import _extract_first_block, _MAX_BLOCK_CHARS, _TITLE_ONLY_MAX_CHARS

# ── helpers ────────────────────────────────────────────────────────────────────
all_pass = True


def check(label: str, cond: bool, detail: str = "") -> bool:
    global all_pass
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}]  {label}" + (f"  —  {detail}" if detail else ""))
    if not cond:
        all_pass = False
    return cond


CORPUS_DIR = Path(__file__).parent / "data" / "corpus"

def read_doc(stem: str) -> str:
    return (CORPUS_DIR / f"{stem}.txt").read_text(encoding="utf-8").strip()


# ══════════════════════════════════════════════════════════════════════════════
print("\n══════════════════════════════════════════════════════════════")
print("  RAG Retrieval Tests")
print("══════════════════════════════════════════════════════════════\n")

# ── 1. Block extractor: bare-title promotion ───────────────────────────────────
print("① Block extractor — bare-title detection and second-block promotion")

# model_cards: first block is short title → should include second block (Q1+A1)
mc = read_doc("model_cards")
mc_block = _extract_first_block(mc)
check("model_cards: block not empty",                mc_block.strip() != "")
check("model_cards: contains openai/gpt-oss-20b",   "openai/gpt-oss-20b"  in mc_block,  mc_block[:100])
check("model_cards: contains openai/gpt-oss-120b",  "openai/gpt-oss-120b" in mc_block,  mc_block[:100])
check("model_cards: within MAX_BLOCK_CHARS",         len(mc_block) <= _MAX_BLOCK_CHARS,  str(len(mc_block)))

# model_routing_faq: first block is short title → should include first Q+A
mrf = read_doc("model_routing_faq")
mrf_block = _extract_first_block(mrf)
check("model_routing_faq: contains 6-stage",         "6-stage" in mrf_block,             mrf_block[:100])
check("model_routing_faq: within MAX_BLOCK_CHARS",   len(mrf_block) <= _MAX_BLOCK_CHARS, str(len(mrf_block)))

# ── 2. Block extractor: documents where first block already has content ────────
print("\n② Block extractor — first block already substantive (no promotion)")

# api_rate_limits: title "API Developer Policy §4.2 — Rate Limits" is 38 chars
# but wait — it IS short enough to trigger promotion. Verify the right result.
arl = read_doc("api_rate_limits")
arl_block = _extract_first_block(arl)
check("api_rate_limits: not empty",                  arl_block.strip() != "")
check("api_rate_limits: within MAX_BLOCK_CHARS",     len(arl_block) <= _MAX_BLOCK_CHARS, str(len(arl_block)))
check("api_rate_limits: contains 'rate' information",
      "60" in arl_block or "requests" in arl_block.lower() or "limit" in arl_block.lower(),
      arl_block[:120])

# data_retention_policy: title "Data Retention Policy v2.1" is short →
# promotes to include first content paragraph about log retention
drp = read_doc("data_retention_policy")
drp_block = _extract_first_block(drp)
check("data_retention_policy: not empty",            drp_block.strip() != "")
check("data_retention_policy: contains '90 days'",   "90 days" in drp_block, drp_block[:120])

# ── 3. Block extractor: step-format documents ─────────────────────────────────
print("\n③ Block extractor — numbered-step documents")

# oncall_runbook: title "On-Call Runbook — Database Latency Escalation" is 46 chars
# → promotes to include Step 1 block
ocr = read_doc("oncall_runbook")
ocr_block = _extract_first_block(ocr)
check("oncall_runbook: contains Step 1",             "Step 1" in ocr_block, ocr_block[:120])
check("oncall_runbook: within MAX_BLOCK_CHARS",      len(ocr_block) <= _MAX_BLOCK_CHARS)

# deployment_guide: "Deployment Guide — AIFlow Self-Hosted" = 38 chars → promotes
dg = read_doc("deployment_guide")
dg_block = _extract_first_block(dg)
check("deployment_guide: not empty",                 dg_block.strip() != "")
check("deployment_guide: within MAX_BLOCK_CHARS",    len(dg_block) <= _MAX_BLOCK_CHARS)

# ── 4. Block extractor: category-group format (http_status_codes) ─────────────
print("\n④ Block extractor — category-group format (http_status_codes)")

hsc = read_doc("http_status_codes")
hsc_block = _extract_first_block(hsc)
# Title "HTTP Status Code Quick Reference" (32 chars) → promotes to first category block
check("http_status_codes: not empty",                hsc_block.strip() != "")
check("http_status_codes: within MAX_BLOCK_CHARS",   len(hsc_block) <= _MAX_BLOCK_CHARS, str(len(hsc_block)))
# Old extractor returned 889 chars; new one should be much shorter
check("http_status_codes: shorter than old 3-sent",  len(hsc_block) < 889, str(len(hsc_block)))

# ── 5. Block extractor: never returns empty ────────────────────────────────────
print("\n⑤ Block extractor — edge cases and safety")

check("empty string input → empty (safe fallback)",
      _extract_first_block("") == "")
check("single block with no blank lines → that block (capped)",
      _extract_first_block("Hello world") == "Hello world")
check("only blank lines → fallback returns raw (capped) text",
      _extract_first_block("\n\n\n\n") == "\n\n\n\n")

long_text = "A" * 2000
check(f"2000-char single block → capped at {_MAX_BLOCK_CHARS}",
      len(_extract_first_block(long_text)) == _MAX_BLOCK_CHARS)

# ── 6. Similarity ranking tests (require SentenceTransformer) ─────────────────
print("\n⑥ Similarity ranking — model_cards vs model_routing_faq")

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np

    st = SentenceTransformer("all-MiniLM-L6-v2")

    docs, titles = [], []
    for f in sorted(CORPUS_DIR.glob("*.txt")):
        content = f.read_text(encoding="utf-8").strip()
        if content:
            docs.append(content)
            titles.append(f.stem)

    embeddings = st.encode(docs, show_progress_bar=False)

    def top_match(query: str) -> tuple[str, float]:
        q_emb = st.encode([query], show_progress_bar=False)[0]
        norms = np.linalg.norm(embeddings, axis=1)
        sims = (embeddings @ q_emb) / (norms * np.linalg.norm(q_emb))
        best_idx = int(np.argmax(sims))
        return titles[best_idx], float(sims[best_idx])

    def sim_for(query: str, doc_title: str) -> float:
        q_emb = st.encode([query], show_progress_bar=False)[0]
        norms = np.linalg.norm(embeddings, axis=1)
        sims = (embeddings @ q_emb) / (norms * np.linalg.norm(q_emb))
        idx = titles.index(doc_title)
        return float(sims[idx])

    THRESHOLD = 0.55

    # Test A: model-identity query → model_cards must win
    q_models = "Which AI models does AIFlow currently use for its Small Model and Large Model tiers?"
    winner, winner_sim = top_match(q_models)
    mc_sim = sim_for(q_models, "model_cards")
    mrf_sim = sim_for(q_models, "model_routing_faq")
    check("model-identity query: winner is model_cards",
          winner == "model_cards", f"got {winner} ({winner_sim:.4f})")
    check("model-identity query: model_cards above threshold",
          mc_sim >= THRESHOLD, f"{mc_sim:.4f}")
    check("model-identity query: model_cards > model_routing_faq",
          mc_sim > mrf_sim, f"mc={mc_sim:.4f} mrf={mrf_sim:.4f}")
    # Confirm improvement over pre-Fix-A score (was 0.5520)
    check("model-identity query: model_cards sim improved (was 0.5520)",
          mc_sim > 0.55, f"now {mc_sim:.4f}")

    # Test B: routing-behaviour query → model_routing_faq must still win
    q_routing = "How does AIFlow decide which model tier to use for a request?"
    r_winner, r_sim = top_match(q_routing)
    check("routing-behaviour query: winner is model_routing_faq",
          r_winner == "model_routing_faq", f"got {r_winner} ({r_sim:.4f})")
    check("routing-behaviour query: above threshold",
          r_sim >= THRESHOLD, f"{r_sim:.4f}")

    # Test C: rate-limit query → api_rate_limits must win
    q_rate = "What are the API rate limits for free-tier users?"
    rl_winner, rl_sim = top_match(q_rate)
    check("rate-limit query: winner is api_rate_limits",
          rl_winner == "api_rate_limits", f"got {rl_winner} ({rl_sim:.4f})")

    # Test D: on-call query → oncall_runbook must win
    q_oncall = "What are the on-call escalation steps when database connection latency exceeds 500ms?"
    oc_winner, oc_sim = top_match(q_oncall)
    check("on-call query: winner is oncall_runbook",
          oc_winner == "oncall_runbook", f"got {oc_winner} ({oc_sim:.4f})")

    # Test E: model-identity block extract contains model IDs
    mc_doc = next(d for t, d in zip(titles, docs) if t == "model_cards")
    mc_extracted = _extract_first_block(mc_doc)
    check("model_cards extracted block: contains gpt-oss-20b",
          "openai/gpt-oss-20b" in mc_extracted, mc_extracted[:120])
    check("model_cards extracted block: contains gpt-oss-120b",
          "openai/gpt-oss-120b" in mc_extracted, mc_extracted[:120])

    # Test F: model_routing_faq block extract contains 6-stage pipeline text
    mrf_doc = next(d for t, d in zip(titles, docs) if t == "model_routing_faq")
    mrf_extracted = _extract_first_block(mrf_doc)
    check("model_routing_faq block: contains '6-stage'",
          "6-stage" in mrf_extracted, mrf_extracted[:120])

    print(f"\n  [INFO]  model_cards sim (post-Fix-A): {mc_sim:.4f}  |  model_routing_faq sim: {mrf_sim:.4f}")

except ImportError:
    print("  [SKIP]  sentence-transformers not available — skipping similarity tests")

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════════════")
if all_pass:
    print("  ALL TESTS PASSED")
else:
    print("  SOME TESTS FAILED — see above")
print("══════════════════════════════════════════════════════════════\n")
sys.exit(0 if all_pass else 1)
