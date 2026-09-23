"""
Train the complexity classifier.
Run from the backend/ directory:
  python scripts/train_classifier.py

Outputs:
  data/classifier.joblib        — fitted sklearn model
  data/classifier_metrics.json  — accuracy and AUC on held-out test set
"""
import sys
import logging
from pathlib import Path

# Ensure backend/ is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from sentence_transformers import SentenceTransformer

def main():
    print("Loading sentence transformer model (all-MiniLM-L6-v2)…")
    st_model = SentenceTransformer("all-MiniLM-L6-v2")

    def encode_fn(texts):
        return st_model.encode(texts, show_progress_bar=True, batch_size=32).tolist()

    from engine.classifier import train
    print("Training classifier…")
    metrics = train(encode_fn=encode_fn)
    print("\n" + "="*50)
    print(f"  Accuracy (held-out): {metrics['accuracy']:.4f}")
    print(f"  AUC (held-out):      {metrics['auc']:.4f}")
    print(f"  Train size:          {metrics['n_train']}")
    print(f"  Test size:           {metrics['n_test']}")
    print("="*50)
    print("Model saved to data/classifier.joblib")
    print("Metrics saved to data/classifier_metrics.json")

if __name__ == "__main__":
    main()
