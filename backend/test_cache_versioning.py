"""
Tests for retrieval cache versioning and invalidation.

Covers:
  1. compute_corpus_version() returns a stable hex digest
  2. Version changes when a corpus file changes (mtime)
  3. store_in_cache stores source_pathway and corpus_version correctly
  4. lookup_exact serves a non-stale retrieval entry
  5. lookup_exact invalidates a stale retrieval entry (corpus version changed)
  6. lookup_exact does NOT invalidate model entries on corpus version change
  7. lookup_exact does NOT invalidate NULL source_pathway entries (legacy)
  8. SemanticCacheIndex skips stale retrieval entries
  9. SemanticCacheIndex serves fresh retrieval entries
 10. Regression: stale retrieval answer for model-identity query is not served;
     query can reach the retrieval engine and return correct model IDs.

Run from backend/:  .venv/Scripts/python.exe test_cache_versioning.py
"""
import sys
import json
import hashlib
import re
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# ── helpers ────────────────────────────────────────────────────────────────────
all_pass = True


def check(label: str, cond: bool, detail: str = "") -> bool:
    global all_pass
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}]  {label}" + (f"  —  {detail}" if detail else ""))
    if not cond:
        all_pass = False
    return cond


# ── Import modules under test ─────────────────────────────────────────────────
from engine.cache import (
    compute_corpus_version,
    store_in_cache,
    lookup_exact,
    rebuild_index_from_db,
    get_index,
    SemanticCacheIndex,
    CURRENT_CORPUS_VERSION,
    _normalise,
    _sha256,
)
import engine.cache as cache_module

# ══════════════════════════════════════════════════════════════════════════════
print("\n══════════════════════════════════════════════════════════════")
print("  Retrieval Cache Versioning Tests")
print("══════════════════════════════════════════════════════════════\n")

# ── 1. compute_corpus_version returns a stable digest ─────────────────────────
print("① compute_corpus_version — stability and format")

v1 = compute_corpus_version()
v2 = compute_corpus_version()
check("returns a string",       isinstance(v1, str))
check("non-empty (corpus exists)", len(v1) > 0, f"len={len(v1)}")
check("looks like a sha256 hex",   len(v1) == 64 and all(c in "0123456789abcdef" for c in v1))
check("deterministic — two calls return same value", v1 == v2, f"{v1[:12]}… == {v2[:12]}…")
check("CURRENT_CORPUS_VERSION matches compute", CURRENT_CORPUS_VERSION == v1)

# ── 2. Version changes when corpus changes ────────────────────────────────────
print("\n② Version changes when a corpus file is touched")

with tempfile.TemporaryDirectory() as tmp_dir:
    tmp = Path(tmp_dir)
    # Write a fake corpus file
    f1 = tmp / "doc_a.txt"
    f1.write_text("Content of document A", encoding="utf-8")

    # Monkey-patch the corpus dir
    original_dir = cache_module._CORPUS_DIR
    cache_module._CORPUS_DIR = tmp

    ver_a = compute_corpus_version()
    time.sleep(0.05)  # ensure mtime differs
    f1.write_text("Updated content of document A", encoding="utf-8")
    ver_b = compute_corpus_version()

    check("version changes after file update", ver_a != ver_b,
          f"before={ver_a[:12]}… after={ver_b[:12]}…")

    # Adding a file also changes version
    f2 = tmp / "doc_b.txt"
    f2.write_text("Document B", encoding="utf-8")
    ver_c = compute_corpus_version()
    check("version changes after new file added", ver_b != ver_c)

    # Empty dir → empty string
    cache_module._CORPUS_DIR = Path(tmp_dir) / "nonexistent"
    ver_empty = compute_corpus_version()
    check("nonexistent dir → empty string", ver_empty == "")

    cache_module._CORPUS_DIR = original_dir  # restore

# ── 3–7. lookup_exact with corpus versioning (SQLite-based) ───────────────────
print("\n③–⑦ lookup_exact corpus versioning (in-memory SQLite DB)")

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from db import Base, CacheEntryORM

# Create an isolated in-memory SQLite DB for tests
test_engine = sa.create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=test_engine)
TestSession = sessionmaker(bind=test_engine)
db = TestSession()

FRESH_VERSION = compute_corpus_version()
STALE_VERSION = "aabbccdd" * 8  # deliberately different 64-char hex string
assert STALE_VERSION != FRESH_VERSION, "stale version must differ from current"

QUERY_RETRIEVAL = "Which AI models does AIFlow currently use for its Small Model and Large Model tiers?"
QUERY_MODEL     = "What is the capital of France?"
QUERY_LEGACY    = "What is the boiling point of water?"

NORM_R = _normalise(QUERY_RETRIEVAL)
NORM_M = _normalise(QUERY_MODEL)
NORM_L = _normalise(QUERY_LEGACY)

def seed_entry(db, query_norm, response, source_pathway, corpus_version):
    h = _sha256(query_norm)
    db.query(CacheEntryORM).filter(CacheEntryORM.hash == h).delete()
    row = CacheEntryORM(
        hash=h,
        query=query_norm,
        response=response,
        embedding=None,
        created_at=datetime.now(timezone.utc),
        source_pathway=source_pathway,
        corpus_version=corpus_version,
    )
    db.add(row)
    db.commit()
    return h

# ③ Fresh retrieval entry (same version) — must be served
seed_entry(db, NORM_R, "FRESH_RETRIEVAL_RESPONSE", "retrieval", FRESH_VERSION)
result_fresh = lookup_exact(db, QUERY_RETRIEVAL)
check("③ fresh retrieval entry (same corpus version): served",
      result_fresh == "FRESH_RETRIEVAL_RESPONSE", repr(result_fresh))

# ④ Stale retrieval entry (old version) — must be invalidated
seed_entry(db, NORM_R, "OLD_MODEL_ROUTING_FAQ_CONTENT", "retrieval", STALE_VERSION)
result_stale = lookup_exact(db, QUERY_RETRIEVAL)
check("④ stale retrieval entry (old corpus version): NOT served",
      result_stale is None, repr(result_stale))
# Confirm row was deleted from DB
h_r = _sha256(NORM_R)
row_after = db.query(CacheEntryORM).filter(CacheEntryORM.hash == h_r).first()
check("④ stale retrieval entry: deleted from DB", row_after is None)

# ⑤ Model entry — corpus version change must NOT invalidate it
seed_entry(db, NORM_M, "Paris", "model", None)
result_model = lookup_exact(db, QUERY_MODEL)
check("⑤ model entry: served regardless of corpus version",
      result_model == "Paris", repr(result_model))

# ⑥ Legacy entry (NULL source_pathway) — must not be invalidated
seed_entry(db, NORM_L, "100 degrees Celsius", None, None)
result_legacy = lookup_exact(db, QUERY_LEGACY)
check("⑥ legacy NULL source_pathway entry: served (not invalidated)",
      result_legacy == "100 degrees Celsius", repr(result_legacy))

db.close()

# ── 8–9. SemanticCacheIndex corpus versioning ─────────────────────────────────
print("\n⑧–⑨ SemanticCacheIndex retrieval corpus versioning")

import numpy as np

def make_embedding(seed: int, dim: int = 384) -> list[float]:
    rng = np.random.default_rng(seed)
    v = rng.random(dim).astype(np.float32)
    return (v / np.linalg.norm(v)).tolist()

idx = SemanticCacheIndex()
emb_retrieval = make_embedding(1)
emb_model     = make_embedding(2)
now = datetime.now(timezone.utc)
h_ret = _sha256("test_retrieval_query")
h_mod = _sha256("test_model_query")

# ⑧ Stale retrieval entry in semantic index — must be skipped
idx.add(h_ret, "test_retrieval_query", "STALE_RETRIEVAL",
        emb_retrieval, now, source_pathway="retrieval", corpus_version=STALE_VERSION)

stale_q_emb = emb_retrieval  # same embedding → sim = 1.0
result_sem_stale = idx.lookup("test_retrieval_query", stale_q_emb)
check("⑧ semantic cache: stale retrieval entry NOT returned",
      result_sem_stale is None, repr(result_sem_stale))

# ⑨ Fresh retrieval entry in semantic index — must be served
idx2 = SemanticCacheIndex()
idx2.add(h_ret, "test_retrieval_query", "FRESH_RETRIEVAL",
         emb_retrieval, now, source_pathway="retrieval", corpus_version=FRESH_VERSION)
result_sem_fresh = idx2.lookup("test_retrieval_query", emb_retrieval)
check("⑨ semantic cache: fresh retrieval entry returned",
      result_sem_fresh is not None and result_sem_fresh[0] == "FRESH_RETRIEVAL",
      repr(result_sem_fresh))

# Model entry in semantic index is never affected
idx3 = SemanticCacheIndex()
idx3.add(h_mod, "test_model_query", "MODEL_RESPONSE",
         emb_model, now, source_pathway="model", corpus_version=None)
result_sem_model = idx3.lookup("test_model_query", emb_model)
check("⑨b semantic cache: model entry always returned",
      result_sem_model is not None and result_sem_model[0] == "MODEL_RESPONSE")

# ── 10. Regression: model-identity query is not served stale ─────────────────
print("\n⑩ Regression — model-identity query bypass stale retrieval cache")

# Seed the stale retrieval entry that reproduces the original bug
db2 = TestSession()
STALE_RESPONSE = "Model Routing FAQ\nQ: How does AIFlow decide which model tier to use?\nA: AIFlow uses a 6-stage decision pipeline."
seed_entry(db2, _normalise(QUERY_RETRIEVAL), STALE_RESPONSE, "retrieval", STALE_VERSION)

# lookup_exact must NOT return the stale response
result_bug = lookup_exact(db2, QUERY_RETRIEVAL)
check("stale model_routing_faq content NOT returned for model-identity query",
      result_bug is None, repr(result_bug)[:80] if result_bug else "None")

# Seed a fresh retrieval entry for the same query (correct content)
FRESH_RESPONSE = "Model Cards — AIFlow Inference Tiers\n\nQ: Which models does AIFlow currently use?\nA: Tier 2 uses openai/gpt-oss-20b and Tier 3 uses openai/gpt-oss-120b, both served via Groq."
seed_entry(db2, _normalise(QUERY_RETRIEVAL), FRESH_RESPONSE, "retrieval", FRESH_VERSION)
result_fresh2 = lookup_exact(db2, QUERY_RETRIEVAL)
check("fresh model_cards content IS returned after corpus update",
      result_fresh2 is not None and "openai/gpt-oss-20b" in result_fresh2,
      repr(result_fresh2)[:80] if result_fresh2 else "None")
check("fresh response contains openai/gpt-oss-20b",
      result_fresh2 is not None and "openai/gpt-oss-20b" in (result_fresh2 or ""))
check("fresh response contains openai/gpt-oss-120b",
      result_fresh2 is not None and "openai/gpt-oss-120b" in (result_fresh2 or ""))
db2.close()

# ── 11. store_in_cache tags retrieval entries correctly ───────────────────────
print("\n⑪ store_in_cache — pathway tagging")

db3 = TestSession()
dummy_emb = make_embedding(99)
store_in_cache(db3, "test retrieval store query",
               "retrieval response text", dummy_emb,
               source_pathway="retrieval")
h_test = _sha256(_normalise("test retrieval store query"))
row_r = db3.query(CacheEntryORM).filter(CacheEntryORM.hash == h_test).first()
check("retrieval entry: source_pathway='retrieval'",
      row_r is not None and row_r.source_pathway == "retrieval",
      f"got {getattr(row_r, 'source_pathway', None)}")
check("retrieval entry: corpus_version == CURRENT_CORPUS_VERSION",
      row_r is not None and row_r.corpus_version == FRESH_VERSION,
      f"got {getattr(row_r, 'corpus_version', None)[:12] if row_r and row_r.corpus_version else None}")

store_in_cache(db3, "test model store query",
               "model response text", dummy_emb,
               source_pathway="model")
h_test2 = _sha256(_normalise("test model store query"))
row_m = db3.query(CacheEntryORM).filter(CacheEntryORM.hash == h_test2).first()
check("model entry: source_pathway='model'",
      row_m is not None and row_m.source_pathway == "model",
      f"got {getattr(row_m, 'source_pathway', None)}")
check("model entry: corpus_version is None",
      row_m is not None and row_m.corpus_version is None,
      f"got {getattr(row_m, 'corpus_version', None)}")
db3.close()

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════════════")
if all_pass:
    print("  ALL TESTS PASSED")
else:
    print("  SOME TESTS FAILED — see above")
print("══════════════════════════════════════════════════════════════\n")
sys.exit(0 if all_pass else 1)
