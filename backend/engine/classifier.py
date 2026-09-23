"""
Stage 5 — Complexity Classifier

Trains a scikit-learn LogisticRegression on a labelled prompt dataset.
Features: MiniLM embedding (384-d) + [log(token_count+1), question_mark_count,
          has_code_block, has_document_flag, imperative_verb_flag]

The fitted model is persisted with joblib so it isn't retrained on every restart.
Training metrics (accuracy, AUC) are saved to data/classifier_metrics.json
and stored in the DB so the /v1/audit endpoint can report them honestly.
"""
from __future__ import annotations
import json
import logging
import math
import re
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH   = Path(__file__).parent.parent / "data" / "classifier.joblib"
METRICS_PATH = Path(__file__).parent.parent / "data" / "classifier_metrics.json"
TRAINING_DATA_PATH = Path(__file__).parent.parent / "data" / "training_prompts.json"

# MiniLM embedding dimension
EMBED_DIM = 384


def _extract_features(text: str, embedding: list[float]) -> np.ndarray:
    """Concatenate embedding with 5 handcrafted features."""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    token_count = len(enc.encode(text))

    log_tokens         = math.log(token_count + 1)
    question_marks     = text.count("?")
    has_code_block     = 1.0 if "```" in text or "`" in text else 0.0
    has_document_flag  = 1.0 if re.search(
        r"\b(document|file|attached|pdf|paste|above text|following text)\b", text, re.I
    ) else 0.0
    imperative_verb    = 1.0 if re.match(
        r"^\s*(write|generate|create|list|summarize|analyze|explain|describe|"
        r"compare|review|draft|rewrite|translate|fix|debug|refactor|identify|"
        r"evaluate|critique|assess)\b", text, re.I
    ) else 0.0

    handcrafted = np.array([
        log_tokens, question_marks, has_code_block,
        has_document_flag, imperative_verb,
    ], dtype=np.float32)
    return np.concatenate([np.array(embedding, dtype=np.float32), handcrafted])


def load_model():
    """Load the persisted classifier model, or return None if not trained yet."""
    import joblib
    if MODEL_PATH.exists():
        try:
            clf = joblib.load(MODEL_PATH)
            logger.info("Classifier loaded from %s", MODEL_PATH)
            return clf
        except Exception as exc:
            logger.warning("Failed to load classifier: %s", exc)
    return None


_clf = None   # module-level cache


def get_classifier():
    global _clf
    if _clf is None:
        _clf = load_model()
    return _clf


def predict(text: str, embedding: list[float]) -> float:
    """
    Returns p_small (0..1): probability that the small model is sufficient.
    Falls back to 0.5 if classifier is not trained.
    """
    clf = get_classifier()
    if clf is None:
        logger.warning("Classifier not trained — returning p_small=0.5 fallback")
        return 0.5
    try:
        feats = _extract_features(text, embedding).reshape(1, -1)
        proba = clf.predict_proba(feats)[0]
        # label=1 means "small model sufficient"
        classes = list(clf.classes_)
        if 1 in classes:
            return float(proba[classes.index(1)])
        return float(proba[1])
    except Exception as exc:
        logger.error("Classifier predict error: %s", exc)
        return 0.5


def train(encode_fn=None, db=None) -> dict:
    """
    Train the classifier from training_prompts.json.
    Returns a dict with accuracy, auc, n_train, n_test.
    Persists model to MODEL_PATH and metrics to METRICS_PATH + DB.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, roc_auc_score
    import joblib
    from datetime import datetime, timezone

    if not TRAINING_DATA_PATH.exists():
        raise FileNotFoundError(f"Training data not found: {TRAINING_DATA_PATH}")

    with open(TRAINING_DATA_PATH) as f:
        data = json.load(f)

    prompts = [d["prompt"] for d in data]
    labels  = [d["label"]  for d in data]

    logger.info("Training classifier on %d examples…", len(prompts))

    # Embed all prompts
    if encode_fn is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        encode_fn = lambda texts: _model.encode(texts, show_progress_bar=False).tolist()

    embeddings = encode_fn(prompts)

    # Build feature matrix
    X = np.array([
        _extract_features(p, e) for p, e in zip(prompts, embeddings)
    ])
    y = np.array(labels)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )

    clf = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)

    y_pred  = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, list(clf.classes_).index(1)]

    accuracy = float(accuracy_score(y_test, y_pred))
    auc      = float(roc_auc_score(y_test, y_proba))

    logger.info("Classifier trained — accuracy=%.4f  AUC=%.4f  n_train=%d  n_test=%d",
                accuracy, auc, len(X_train), len(X_test))

    # Persist model
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)

    metrics = {
        "accuracy": round(accuracy, 4),
        "auc":      round(auc, 4),
        "n_train":  int(len(X_train)),
        "n_test":   int(len(X_test)),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    # Store in DB if session provided
    if db is not None:
        from db import ClassifierMetricsORM
        row = ClassifierMetricsORM(
            accuracy=accuracy,
            auc=auc,
            n_train=len(X_train),
            n_test=len(X_test),
            trained_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.commit()

    # Reset module-level cache
    global _clf
    _clf = clf

    return metrics


def load_metrics() -> Optional[dict]:
    if METRICS_PATH.exists():
        with open(METRICS_PATH) as f:
            return json.load(f)
    return None
