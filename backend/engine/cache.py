"""
Stage 2 — Exact Cache (SHA-256, 24h TTL)
Stage 3 — Semantic Cache (MiniLM cosine similarity)

Never serve from cache if the query contains time-sensitive words or
personalisation markers.

Retrieval cache invalidation
----------------------------
Responses produced by the local corpus retrieval stage are tagged with
source_pathway='retrieval' and a corpus_version fingerprint computed from
the size and mtime of every .txt file in the corpus directory.

When lookup_exact or the semantic cache index returns a retrieval entry,
it compares the stored corpus_version against the current one.  If they
differ, the entry is treated as a miss (and deleted from the DB for the
exact cache).  This prevents stale retrieval answers from masking updated
corpus content after a corpus change.

Model-response entries (source_pathway='model') and entries with NULL
source_pathway (pre-existing rows) are never affected by this check.
"""
from __future__ import annotations
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Words that make a cached response unreliable
_NO_CACHE_PATTERN = re.compile(
    r"\b(today|now|latest|current|recent|this week|this month|this year|"
    r"right now|at the moment|my |this document|attached|upload)\b",
    re.I,
)

# Words indicating a stable factual query (safe for loose semantic cache)
_STABLE_FACTUAL_PATTERN = re.compile(
    r"\b(capital|boiling point|speed of light|atomic number|distance|"
    r"population|height|weight|formula|definition|meaning|abbreviation|"
    r"acronym|symbol|constant|rate|convert|celsius|fahrenheit)\b",
    re.I,
)

_24H = timedelta(hours=24)

EXACT_SIM_THRESHOLD  = 0.95   # always serve
LOOSE_SIM_THRESHOLD  = 0.90   # serve only for stable factual

# ---------------------------------------------------------------------------
# Corpus version fingerprint
# ---------------------------------------------------------------------------
# Computed once per process from file metadata (mtime + size) of every .txt
# file in the corpus directory.  When the corpus changes (file updated, added,
# or removed), the fingerprint changes and all retrieval cache entries written
# under the old fingerprint are treated as stale.
#
# We deliberately do NOT hash file content here — mtime+size is sufficient
# and much faster for 17 small files.  Anyone who manually edits a corpus
# file should touch it (or the OS will update mtime automatically on save).

_CORPUS_DIR = Path(__file__).parent.parent / "data" / "corpus"


def compute_corpus_version() -> str:
    """
    Return a hex digest that uniquely identifies the current state of the
    corpus directory.  The digest covers: sorted filenames, file sizes, and
    last-modified timestamps (integer seconds).

    Returns an empty string if the corpus directory doesn't exist (e.g. in
    test environments where the directory is absent).
    """
    if not _CORPUS_DIR.exists():
        return ""
    parts: list[str] = []
    for f in sorted(_CORPUS_DIR.glob("*.txt")):
        st = f.stat()
        parts.append(f"{f.name}:{st.st_size}:{int(st.st_mtime)}")
    if not parts:
        return ""
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


# Computed once at module import time; shared across all requests in the same
# process.  A restart re-computes it from the current corpus state.
CURRENT_CORPUS_VERSION: str = compute_corpus_version()
logger.debug("Corpus version: %s…", CURRENT_CORPUS_VERSION[:12] if CURRENT_CORPUS_VERSION else "(empty)")


def _normalise(query: str) -> str:
    """Lower, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", query.strip().lower())


def _sha256(normalised: str) -> str:
    return hashlib.sha256(normalised.encode()).hexdigest()


def _is_time_sensitive(query: str) -> bool:
    return bool(_NO_CACHE_PATTERN.search(query))


def _is_stable_factual(query: str) -> bool:
    return bool(_STABLE_FACTUAL_PATTERN.search(query)) and not _is_time_sensitive(query)


# ---------------------------------------------------------------------------
# In-memory embedding matrix (rebuilt from DB on startup, no FAISS needed)
# ---------------------------------------------------------------------------
class SemanticCacheIndex:
    """
    Holds all cached embeddings as a numpy matrix for cosine similarity.
    Not thread-safe for writes (single-process uvicorn is fine).
    """

    def __init__(self) -> None:
        self._hashes:          list[str]      = []
        self._queries:         list[str]      = []
        self._responses:       list[str]      = []
        self._matrix:          Optional[np.ndarray] = None   # shape (N, 384)
        self._created_at:      list[datetime] = []
        self._source_pathways: list[Optional[str]] = []
        self._corpus_versions: list[Optional[str]] = []

    def _cosine(self, vec: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between vec (1, D) and self._matrix (N, D)."""
        if self._matrix is None or len(self._matrix) == 0:
            return np.array([])
        norms = np.linalg.norm(self._matrix, axis=1)
        norms = np.where(norms == 0, 1e-9, norms)
        dot = self._matrix @ vec
        return dot / (norms * (np.linalg.norm(vec) or 1e-9))

    def add(self, hash_: str, query: str, response: str,
            embedding: list[float], created_at: datetime,
            source_pathway: Optional[str] = None,
            corpus_version: Optional[str] = None) -> None:
        if hash_ in self._hashes:
            return
        self._hashes.append(hash_)
        self._queries.append(query)
        self._responses.append(response)
        self._created_at.append(created_at)
        self._source_pathways.append(source_pathway)
        self._corpus_versions.append(corpus_version)
        vec = np.array(embedding, dtype=np.float32)
        if self._matrix is None:
            self._matrix = vec.reshape(1, -1)
        else:
            self._matrix = np.vstack([self._matrix, vec.reshape(1, -1)])

    def lookup(self, query: str, embedding: list[float]) -> Optional[tuple[str, float]]:
        """
        Returns (response, similarity) or None.
        Never serves time-sensitive queries.
        Stale retrieval entries (corpus version mismatch) are skipped.
        """
        if _is_time_sensitive(query):
            return None
        if not self._hashes:
            return None

        vec = np.array(embedding, dtype=np.float32)
        sims = self._cosine(vec)
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])

        # TTL check
        age = datetime.now(timezone.utc) - self._created_at[best_idx].replace(
            tzinfo=timezone.utc if self._created_at[best_idx].tzinfo is None else self._created_at[best_idx].tzinfo
        )
        if age > _24H:
            logger.debug("semantic cache: best match expired (%.2f, age %s)", best_sim, age)
            return None

        # Retrieval corpus version check — skip stale retrieval entries
        if self._source_pathways[best_idx] == "retrieval":
            stored_ver = self._corpus_versions[best_idx]
            if stored_ver != CURRENT_CORPUS_VERSION:
                logger.info(
                    "semantic cache: skipping stale retrieval entry (corpus version changed) "
                    "for %r stored=%s… current=%s…",
                    query[:60],
                    (stored_ver or "")[:12],
                    CURRENT_CORPUS_VERSION[:12],
                )
                return None

        if best_sim >= EXACT_SIM_THRESHOLD:
            logger.info("semantic cache: EXACT hit sim=%.3f for %r", best_sim, query[:60])
            return self._responses[best_idx], best_sim

        if best_sim >= LOOSE_SIM_THRESHOLD and _is_stable_factual(query):
            logger.info("semantic cache: STABLE FACTUAL hit sim=%.3f for %r", best_sim, query[:60])
            return self._responses[best_idx], best_sim

        logger.debug("semantic cache: miss sim=%.3f for %r", best_sim, query[:60])
        return None


# Module-level singleton — populated at startup by the FastAPI lifespan
_index = SemanticCacheIndex()


def get_index() -> SemanticCacheIndex:
    return _index


# ---------------------------------------------------------------------------
# DB helpers (called from decision.py and the FastAPI lifespan)
# ---------------------------------------------------------------------------

def lookup_exact(db, query: str) -> Optional[str]:
    """Check Stage 2 exact cache. Returns response or None.

    Retrieval entries whose corpus_version differs from the current version
    are treated as a miss and deleted from the database.
    """
    if _is_time_sensitive(query):
        return None
    norm = _normalise(query)
    h = _sha256(norm)
    from db import CacheEntryORM
    row = db.query(CacheEntryORM).filter(CacheEntryORM.hash == h).first()
    if row is None:
        return None
    # TTL check
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > _24H:
        db.delete(row)
        db.commit()
        return None
    # Retrieval corpus version check — invalidate stale retrieval entries
    if getattr(row, "source_pathway", None) == "retrieval":
        stored_ver = getattr(row, "corpus_version", None)
        if stored_ver != CURRENT_CORPUS_VERSION:
            logger.info(
                "exact cache: invalidating stale retrieval entry for %r "
                "(corpus version changed: stored=%s… current=%s…)",
                query[:60],
                (stored_ver or "")[:12],
                CURRENT_CORPUS_VERSION[:12],
            )
            db.delete(row)
            db.commit()
            return None
    logger.info("exact cache: hit SHA-256 for %r", query[:60])
    return row.response


def store_in_cache(
    db,
    query: str,
    response: str,
    embedding: list[float],
    source_pathway: str = "model",
) -> None:
    """Persist to exact cache table and add to in-memory semantic index.

    Args:
        source_pathway: "retrieval" or "model".  Retrieval entries carry a
            corpus_version so they can be invalidated when the corpus changes.
    """
    norm = _normalise(query)
    h = _sha256(norm)
    from db import CacheEntryORM
    existing = db.query(CacheEntryORM).filter(CacheEntryORM.hash == h).first()
    now = datetime.now(timezone.utc)
    corpus_ver = CURRENT_CORPUS_VERSION if source_pathway == "retrieval" else None
    if existing:
        existing.response       = response
        existing.embedding      = json.dumps(embedding)
        existing.created_at     = now
        existing.source_pathway = source_pathway
        existing.corpus_version = corpus_ver
    else:
        row = CacheEntryORM(
            hash=h,
            query=query,
            response=response,
            embedding=json.dumps(embedding),
            created_at=now,
            source_pathway=source_pathway,
            corpus_version=corpus_ver,
        )
        db.add(row)
    db.commit()
    _index.add(h, query, response, embedding, now,
               source_pathway=source_pathway,
               corpus_version=corpus_ver)


def rebuild_index_from_db(db) -> None:
    """Called at startup: loads all cache entries into the in-memory index."""
    from db import CacheEntryORM
    rows = db.query(CacheEntryORM).all()
    loaded = 0
    for row in rows:
        if row.embedding:
            try:
                emb = json.loads(row.embedding)
                created = row.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                _index.add(
                    row.hash, row.query, row.response, emb, created,
                    source_pathway=getattr(row, "source_pathway", None),
                    corpus_version=getattr(row, "corpus_version", None),
                )
                loaded += 1
            except Exception:
                pass
    logger.info("Semantic cache index rebuilt: %d entries loaded", loaded)
