"""
Stage 4 — Local Corpus Retrieval

Embeds a small local corpus at startup, then answers queries whose top-1
cosine similarity to the corpus exceeds RETRIEVAL_THRESHOLD (0.55).
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

CORPUS_DIR      = Path(__file__).parent.parent / "data" / "corpus"
RETRIEVAL_THRESHOLD = 0.55


class RetrievalEngine:
    def __init__(self) -> None:
        self._docs:       list[str] = []
        self._titles:     list[str] = []
        self._embeddings: Optional[np.ndarray] = None

    def load(self, encode_fn) -> None:
        """Load all .txt files from CORPUS_DIR and embed them."""
        if not CORPUS_DIR.exists():
            logger.warning("Corpus directory not found: %s", CORPUS_DIR)
            return
        texts = []
        titles = []
        for f in sorted(CORPUS_DIR.glob("*.txt")):
            content = f.read_text(encoding="utf-8").strip()
            if content:
                texts.append(content)
                titles.append(f.stem)
        if not texts:
            logger.warning("No corpus documents found")
            return
        embeddings = encode_fn(texts)
        self._docs       = texts
        self._titles     = titles
        self._embeddings = np.array(embeddings, dtype=np.float32)
        logger.info("Retrieval corpus loaded: %d documents", len(texts))

    def lookup(self, query_embedding: list[float]) -> Optional[tuple[str, str, float]]:
        """
        Returns (title, document_text, similarity) if above threshold, else None.
        """
        if self._embeddings is None or len(self._docs) == 0:
            return None
        vec = np.array(query_embedding, dtype=np.float32)
        norms = np.linalg.norm(self._embeddings, axis=1)
        norms = np.where(norms == 0, 1e-9, norms)
        sims  = (self._embeddings @ vec) / (norms * (np.linalg.norm(vec) or 1e-9))
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        if best_sim >= RETRIEVAL_THRESHOLD:
            logger.info(
                "Retrieval: top-1 '%s' sim=%.3f (threshold %.2f)",
                self._titles[best_idx], best_sim, RETRIEVAL_THRESHOLD,
            )
            return self._titles[best_idx], self._docs[best_idx], best_sim
        logger.debug("Retrieval: miss best sim=%.3f < %.2f", best_sim, RETRIEVAL_THRESHOLD)
        return None


# Module-level singleton
_engine = RetrievalEngine()


def get_retrieval_engine() -> RetrievalEngine:
    return _engine
